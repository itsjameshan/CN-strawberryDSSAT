"""Validate the Python implementation of CROPGRO-Strawberry against DSSAT."""
"""验证Python实现的草莓生长模型与DSSAT官方模型的匹配度"""

import argparse  # 命令行参数解析
import os  # 文件系统交互
import subprocess  # 外部程序调用
from datetime import datetime  # 日期处理
from pathlib import Path  # 面向对象的文件路径
import pandas as pd  # 表格数据处理

# 动态导入Python模型实现
import importlib.util  # 动态导入工具

impl_path = Path(__file__).resolve().parent / "cropgro-strawberry-implementation.py"  # 模型实现文件路径
spec = importlib.util.spec_from_file_location("cropgro_impl", impl_path)  # 从路径创建模块规范
impl_module = importlib.util.module_from_spec(spec)  # 创建模块对象
spec.loader.exec_module(impl_module)  # 执行模块代码
CropgroStrawberry = impl_module.CropgroStrawberry  # 获取模型类定义


def parse_dssat_date(code: str) -> str:
    """将DSSAT的YYDDD日期编码转为ISO格式字符串"""
    year = 2000 + int(code[:2])  # DSSAT年份基于2000年
    doy = int(code[2:])  # 后三位表示年积日
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")  # 转换格式


def parse_srx_file(path: str):
    """从SRX实验文件中解析种植日期和气象站代码"""
    planting_code = None  # 种植日期编码(YYDDD)
    wsta = None  # 气象站ID
    with open(path) as f:  # 读取SRX文件内容
        lines = f.readlines()
    for i, line in enumerate(lines):  # 带索引遍历以便查看下一行
        if line.startswith("@L ID_FIELD") and i + 1 < len(lines):  # 田块信息块
            parts = lines[i + 1].split()  # 分割数据字段
            if len(parts) >= 3:
                wsta = parts[2]  # 第三个字段是气象站代码
        if line.startswith("@P PDATE") and i + 1 < len(lines):  # 种植日期块
            parts = lines[i + 1].split()
            if len(parts) >= 2:
                planting_code = parts[1]  # 第二个字段是种植日期
    planting_date = parse_dssat_date(planting_code) if planting_code else None  # 转换日期格式
    return planting_date, wsta  # 返回元组


def read_wth_file(path: str) -> pd.DataFrame:
    """将DSSAT的.WTH气象文件解析为Pandas DataFrame"""
    with open(path) as f:  # 打开气象文件
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("@DATE"))  # 找到数据起始行
    header = lines[start].split()  # 列名列表
    indices = {h: idx for idx, h in enumerate(header)}  # 列名到索引的映射
    records = []  # 每日气象数据记录
    for line in lines[start + 1 :]:  # 处理每条数据记录
        if not line.strip() or line.startswith("*"):  # 跳过空行和注释
            continue
        parts = line.split()  # 分割数据字段
        code = parts[0]  # 第一个字段是YYDDD日期编码
        date = parse_dssat_date(code)  # 转换日期格式
        rec = {  # 构建每日数据字典
            "date": date,
            "tmax": float(parts[indices["TMAX"]]),  # 日最高温(℃)
            "tmin": float(parts[indices["TMIN"]]),  # 日最低温(℃)
            "solar_radiation": float(parts[indices["SRAD"]]),  # 太阳辐射(MJ/m²)
            "rainfall": float(parts[indices["RAIN"]]) if "RAIN" in indices and len(parts) > indices["RAIN"] else 0.0,  # 降雨量(mm)
            "rh": float(parts[indices["RHUM"]]) if "RHUM" in indices and len(parts) > indices["RHUM"] else 70.0,  # 相对湿度(%)
            "wind_speed": float(parts[indices["WIND"]]) if "WIND" in indices and len(parts) > indices["WIND"] else 2.0,  # 风速(m/s)
        }
        records.append(rec)  # 添加当日记录
    return pd.DataFrame(records)  # 转换为DataFrame


def run_dssat(srx_path: str, dssat_dir: str):
    """调用DSSAT官方程序运行实验"""
    util = Path(dssat_dir).resolve() / "Utilities" / "run_dssat"  # DSSAT运行工具绝对路径
    if not util.exists():  # 检查路径有效性
        raise FileNotFoundError(f"未找到run_dssat工具: {util}")
    subprocess.run(
        [str(util), os.path.basename(srx_path)],  # 执行命令: run_dssat SRX文件
        cwd=os.path.dirname(srx_path),  # 在实验目录运行
        check=True,  # 失败时抛出异常
    )


def read_fortran_output(exp_dir: str) -> pd.DataFrame:
    """读取DSSAT输出的结果文件"""
    summary_path = os.path.join(exp_dir, "summary.csv")  # 首选CSV输出
    if os.path.exists(summary_path):  # 如果存在则加载
        return pd.read_csv(summary_path)
    pg_path = os.path.join(exp_dir, "PlantGro.OUT")  # 备选固定宽度文件
    if os.path.exists(pg_path):
        return pd.read_fwf(pg_path, skiprows=4)  # 跳过前4行表头
    raise FileNotFoundError("未找到DSSAT输出文件")  # 无有效输出


def run_python_model(wth_df: pd.DataFrame, planting_date: str) -> pd.DataFrame:
    """使用Python模型模拟作物生长"""
    soil = {  # 简化土壤参数
        "max_root_depth": 50.0,  # 最大根深(cm)
        "field_capacity": 200.0,  # 田间持水量(mm)
        "wilting_point": 50.0,  # 萎蔫点(mm)
    }
    cultivar = {  # 默认品种参数
        "name": "Generic",  # 品种名
        "tbase": 4.0,  # 基础温度(℃)
        "topt": 22.0,  # 最适温度(℃)
        "tmax_th": 35.0,  # 高温阈值(℃)
        "rue": 2.5,  # 辐射利用效率
        "k_light": 0.6,  # 光衰减系数
        "sla": 0.02,  # 比叶面积
        "potential_fruits_per_crown": 10.0,  # 单株潜在果数
    }
    model = CropgroStrawberry(40.0, planting_date, soil, cultivar)  # 创建模型实例(初始LAI=40)
    return model.simulate_growth(wth_df)  # 运行模拟并返回结果


def generate_report(fort_df: pd.DataFrame, py_df: pd.DataFrame, tolerance: float) -> str:
    """生成验证报告，对比Python和Fortran结果"""
    common_cols = [c for c in fort_df.columns if c in py_df.columns]  # 获取共有列名
    lines = []  # 报告内容行
    max_diff = 0.0  # 记录最大差异值
    for col in common_cols:  # 遍历每个共有列
        if pd.api.types.is_numeric_dtype(fort_df[col]) and pd.api.types.is_numeric_dtype(py_df[col]):
            min_len = min(len(fort_df), len(py_df))  # 确保数据长度一致
            diff = (fort_df[col].iloc[:min_len] - py_df[col].iloc[:min_len]).abs().max()  # 计算绝对差值
            lines.append(f"{col}: 最大绝对差 {diff:.4f}")  # 记录列差异
            if diff > max_diff:
                max_diff = diff
    status = "通过" if max_diff <= tolerance else "未通过"  # 验证结论
    header = f"验证{status}。最大绝对差={max_diff:.4f} (允许误差={tolerance})。"
    return header + "\n" + "\n".join(lines)  # 组合报告内容


def main():
    """验证流程主入口"""
    parser = argparse.ArgumentParser(
        description="Python模型与DSSAT的验证工具",
    )  # 创建参数解析器
    parser.add_argument("srx", help="DSSAT实验文件(.SRX路径)")  # 必需参数
    parser.add_argument(  # 可选参数
        "--dssat-dir",
        default="dssat-csm-os-develop",
        help="DSSAT安装目录(默认: dssat-csm-os-develop)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1.0,
        help="可接受的绝对误差容限(默认: 1.0)",
    )
    parser.add_argument(
        "--report",
        default="validation_report.txt",
        help="验证报告输出路径(默认: validation_report.txt)",
    )
    args = parser.parse_args()  # 解析命令行参数

    planting_date, wsta = parse_srx_file(args.srx)  # 解析SRX文件
    if planting_date is None or wsta is None:  # 验证必要参数
        raise ValueError("SRX文件解析失败")

    run_dssat(args.srx, args.dssat_dir)  # 运行DSSAT官方模型

    exp_dir = os.path.dirname(args.srx)  # 实验文件目录
    fort_df = read_fortran_output(exp_dir)  # 读取DSSAT输出

    year = planting_date[:4]  # 提取年份
    weather_dir = os.path.join("dssat-csm-data-develop", "Weather")  # 气象数据目录
    matches = [  # 查找匹配的气象文件
        f for f in os.listdir(weather_dir)
        if f.startswith(f"{wsta}{year[2:]}") and f.endswith(".WTH")
    ]
    if not matches:
        raise FileNotFoundError("未找到匹配的气象文件")
    wth_path = os.path.join(weather_dir, matches[0])  # 取第一个匹配文件
    wth_df = read_wth_file(wth_path)  # 读取气象数据

    py_df = run_python_model(wth_df, planting_date)  # 运行Python模型

    report = generate_report(fort_df, py_df, args.tolerance)  # 生成对比报告
    with open(args.report, "w") as f:  # 写入报告文件
        f.write(report)
    print(report)  # 同时打印到控制台


if __name__ == "__main__":
    main() 