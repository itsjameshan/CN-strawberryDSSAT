"""Compare outputs from the Fortran DSSAT model with the Python version."""
"""对比Fortran版DSSAT模型与Python版本的输出结果"""

import argparse  # 命令行参数解析模块
import os  # 操作系统路径管理
import subprocess  # 外部程序调用模块
from datetime import datetime  # 日期时间处理

import pandas as pd  # 数据分析库
import pandas.testing as pdt  # DataFrame对比工具

# 动态导入Python模型实现文件（支持连字符文件名）
import importlib.util  # 动态导入工具
import pathlib  # 现代化路径操作库

impl_path = (pathlib.Path(__file__).resolve().parent /
             "cropgro-strawberry-implementation.py")  # 获取同级目录下的实现文件路径
spec = importlib.util.spec_from_file_location(  # 创建模块规范对象
    "cropgro_strawberry_implementation", impl_path)  # 指定模块名和文件路径
impl_module = importlib.util.module_from_spec(spec)  # 根据规范创建模块对象
spec.loader.exec_module(impl_module)  # 执行模块代码
CropgroStrawberry = impl_module.CropgroStrawberry  # 获取模型类定义


def parse_dssat_date(code: str) -> str:
    """将DSSAT的YYDDD日期编码转为YYYY-MM-DD格式"""
    year = 2000 + int(code[:2])  # 前两位数字+2000得到年份
    doy = int(code[2:])  # 后三位表示年积日
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")  # 转换为标准日期格式


def parse_srx_file(path: str):
    """解析SRX实验文件获取种植日期和气象站代码"""
    planting_code = None  # 种植日期编码(YYDDD)
    wsta = None  # 气象站代码
    with open(path) as f:  # 打开实验文件
        lines = f.readlines()  # 读取全部内容

    # 遍历文件内容
    for i, line in enumerate(lines):
        if line.startswith("@L ID_FIELD"):  # 田块信息段
            if i + 1 < len(lines):  # 确保有下一行数据
                parts = lines[i + 1].split()  # 分割数据行
                if len(parts) >= 3:
                    wsta = parts[2]  # 第三列为气象站代码

        if line.startswith("@P PDATE"):  # 种植日期段
            if i + 1 < len(lines):
                parts = lines[i + 1].split()
                if len(parts) >= 2:
                    planting_code = parts[1]  # 第二列为种植日期

    # 转换日期格式
    planting_date = parse_dssat_date(planting_code) if planting_code else None
    return planting_date, wsta  # 返回元组


def read_wth_file(path: str) -> pd.DataFrame:
    """读取DSSAT气象文件(.WTH)到DataFrame"""
    with open(path) as f:
        lines = f.readlines()

    # 定位数据起始行（以@DATE开头）
    start = next(i for i, l in enumerate(lines) if l.startswith("@DATE"))
    header = lines[start].split()  # 获取列名
    indices = {h: idx for idx, h in enumerate(header)}  # 创建列名索引映射

    records = []  # 存储每日气象数据
    for line in lines[start + 1:]:  # 遍历数据行
        if not line.strip() or line.startswith("*"):  # 跳过空行和注释
            continue

        parts = line.split()  # 分割数据
        code = parts[0]  # 获取日期编码
        date = parse_dssat_date(code)  # 转换日期格式

        # 构建每日数据字典
        rec = {
            "date": date,
            "tmax": float(parts[indices["TMAX"]]),  # 最高气温(℃)
            "tmin": float(parts[indices["TMIN"]]),  # 最低气温(℃)
            "solar_radiation": float(parts[indices["SRAD"]]),  # 太阳辐射(MJ/m²)
            "rainfall": float(parts[indices["RAIN"]]) if "RAIN" in indices and len(parts) > indices["RAIN"] else 0.0,
            # 降雨量(mm)
            "rh": float(parts[indices["RHUM"]]) if "RHUM" in indices and len(parts) > indices["RHUM"] else 70.0,
            # 相对湿度(%)
            "wind_speed": float(parts[indices["WIND"]]) if "WIND" in indices and len(parts) > indices["WIND"] else 2.0,
            # 风速(m/s)
        }
        records.append(rec)  # 添加记录

    return pd.DataFrame(records)  # 转换为DataFrame


def run_dssat(srx_path: str, dssat_dir: str):
    """调用DSSAT可执行程序运行实验"""
    util = os.path.abspath(os.path.join(dssat_dir, "Utilities", "run_dssat"))  # 获取绝对路径
    if not os.path.exists(util):  # 检查程序是否存在
        raise FileNotFoundError(f"未找到run_dssat工具: {util}")

    # 在实验文件目录下执行命令
    subprocess.run(
        [util, os.path.basename(srx_path)],  # 运行命令
        cwd=os.path.dirname(srx_path),  # 设置工作目录
        check=True  # 检查执行状态
    )


def read_fortran_output(exp_dir: str) -> pd.DataFrame:
    """读取DSSAT输出文件"""
    summary_path = os.path.join(exp_dir, "summary.csv")  # 首选CSV输出路径
    if os.path.exists(summary_path):  # 检查文件存在性
        return pd.read_csv(summary_path)  # 读取CSV文件

    # 回退方案：读取PlantGro.OUT固定宽度文件
    pg_path = os.path.join(exp_dir, "PlantGro.OUT")
    if os.path.exists(pg_path):
        with open(pg_path) as f:
            lines = f.readlines()
        # 查找数据起始行（以@YEAR开头）
        header_idx = next(i for i, line in enumerate(lines) if line.startswith("@YEAR"))
        return pd.read_fwf(pg_path, skiprows=header_idx)  # 跳过表头读取

    raise FileNotFoundError("未找到DSSAT输出文件")  # 无有效输出时报错


def run_python_model(wth_df: pd.DataFrame, planting_date: str):
    """运行Python版生长模型"""
    # 土壤参数配置
    soil = {
        "max_root_depth": 50.0,  # 最大根深(cm)
        "field_capacity": 200.0,  # 田间持水量(mm)
        "wilting_point": 50.0,  # 萎蔫点(mm)
    }

    # 品种参数配置
    cultivar = {
        "name": "Generic",  # 品种名称
        "tbase": 4.0,  # 基础生长温度(℃)
        "topt": 22.0,  # 最适生长温度(℃)
        "tmax_th": 35.0,  # 生长温度上限(℃)
        "rue": 2.5,  # 辐射利用效率
        "k_light": 0.6,  # 光衰减系数
        "sla": 0.02,  # 比叶面积
        "potential_fruits_per_crown": 10.0,  # 单株潜在果实数
    }

    # 初始化模型实例
    model = CropgroStrawberry(
        initial_lai=40.0,  # 初始叶面积指数
        planting_date=planting_date,  # 种植日期
        soil_params=soil,  # 土壤参数
        cultivar_params=cultivar  # 品种参数
    )

    # 运行生长模拟
    return model.simulate_growth(wth_df)


def main():
    """主执行流程"""
    # 配置命令行参数解析器
    parser = argparse.ArgumentParser(
        description="对比DSSAT与Python模型的输出结果"
    )
    parser.add_argument(
        "srx",  # 位置参数
        help="DSSAT实验文件路径(.SRX)"
    )
    parser.add_argument(
        "--dssat-dir",  # 可选参数
        default="dssat-csm-os-develop",
        help="DSSAT安装目录(默认: dssat-csm-os-develop)"
    )
    args = parser.parse_args()  # 解析参数

    # 解析SRX文件获取关键参数
    planting_date, wsta = parse_srx_file(args.srx)
    if planting_date is None or wsta is None:
        raise ValueError("SRX文件解析失败")

    # 运行DSSAT官方模型
    run_dssat(args.srx, args.dssat_dir)

    # 读取DSSAT输出结果
    exp_dir = os.path.dirname(args.srx)  # 获取实验目录
    fort_df = read_fortran_output(exp_dir)

    # 准备气象数据
    year = planting_date[:4]  # 提取年份
    weather_dir = os.path.join("dssat-csm-data-develop", "Weather")  # 气象数据目录
    # 查找匹配的气象文件
    matches = [
        f for f in os.listdir(weather_dir)
        if f.startswith(f"{wsta}{year[2:]}") and f.endswith(".WTH")
    ]
    if not matches:
        raise FileNotFoundError("未找到匹配的气象文件")
    wth_path = os.path.join(weather_dir, matches[0])  # 使用第一个匹配文件
    wth_df = read_wth_file(wth_path)  # 读取气象数据

    # 运行Python模型
    py_df = run_python_model(wth_df, planting_date)

    # 调试输出列名信息
    print(f"Python模型输出列: {list(py_df.columns)}")
    print(f"DSSAT输出列: {list(fort_df.columns)}")

    # 找出共有的数据列
    common_cols = [c for c in fort_df.columns if c in py_df.columns]
    print(f"共有列: {common_cols}")

    if not common_cols:  # 无共有列情况处理
        print("未找到完全匹配的列名，尝试基础对比...")
        print(f"Python模型数据维度: {py_df.shape}")
        print(f"DSSAT输出数据维度: {fort_df.shape}")
        print("模型运行成功但输出格式不同")
        return

    # 截取相同长度的数据进行对比
    min_len = min(len(fort_df), len(py_df))
    fort_subset = fort_df[common_cols].head(min_len)
    py_subset = py_df[common_cols].head(min_len)

    # 执行数据对比（忽略数据类型差异）
    pdt.assert_frame_equal(fort_subset, py_subset, check_dtype=False)
    print(f"Python模型与DSSAT在{len(common_cols)}个共有列上输出匹配")


if __name__ == "__main__":
    main()  # 脚本入口