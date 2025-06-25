#!/usr/bin/env python3
"""只运行Python草莓模型的简化脚本，不依赖DSSAT构建"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# 导入草莓模型实现
import importlib.util
import pathlib

impl_path = pathlib.Path(__file__).resolve().parent / "cropgro-strawberry-implementation.py"
spec = importlib.util.spec_from_file_location("cropgro_strawberry_implementation", impl_path)

if spec is None:
    raise ImportError(f"无法加载模块: {impl_path}")

impl_module = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise ImportError(f"无法获取模块加载器: {impl_path}")

spec.loader.exec_module(impl_module)
CropgroStrawberry = impl_module.CropgroStrawberry


def parse_dssat_date(code: str) -> str:
    """将 DSSAT YYDDD 日期码转换为 YYYY-MM-DD 字符串。"""
    year = 2000 + int(code[:2])
    doy = int(code[2:])
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")


def parse_srx_file(path: str):
    """从 SRX 文件中提取种植日期和气象站代码。"""
    planting_code = None
    wsta = None
    with open(path) as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith("@L ID_FIELD"):
            if i + 1 < len(lines):
                parts = lines[i + 1].split()
                if len(parts) >= 3:
                    wsta = parts[2]
        if line.startswith("@P PDATE"):
            if i + 1 < len(lines):
                parts = lines[i + 1].split()
                if len(parts) >= 2:
                    planting_code = parts[1]
    planting_date = parse_dssat_date(planting_code) if planting_code else None
    return planting_date, wsta


def read_wth_file(path: str) -> pd.DataFrame:
    """将 DSSAT .WTH 文件解析为 DataFrame。"""
    with open(path) as f:
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("@DATE"))
    header = lines[start].split()
    indices = {h: idx for idx, h in enumerate(header)}
    records = []
    for line in lines[start + 1 :]:
        if not line.strip() or line.startswith("*"):
            continue
        parts = line.split()
        code = parts[0]
        date = parse_dssat_date(code)
        rec = {
            "date": date,
            "tmax": float(parts[indices["TMAX"]]),
            "tmin": float(parts[indices["TMIN"]]),
            "solar_radiation": float(parts[indices["SRAD"]]),
            "rainfall": float(parts[indices["RAIN"]]) if "RAIN" in indices and len(parts) > indices["RAIN"] else 0.0,
            "rh": float(parts[indices["RHUM"]]) if "RHUM" in indices and len(parts) > indices["RHUM"] else 70.0,
            "wind_speed": float(parts[indices["WIND"]]) if "WIND" in indices and len(parts) > indices["WIND"] else 2.0,
        }
        records.append(rec)
    return pd.DataFrame(records)


def run_python_model(wth_df: pd.DataFrame, planting_date: str):
    """使用Python模型模拟生长。"""
    soil = {"max_root_depth": 50.0, "field_capacity": 200.0, "wilting_point": 50.0}
    cultivar = {
        "name": "Generic",
        "tbase": 4.0,
        "topt": 22.0,
        "tmax_th": 35.0,
        "rue": 2.5,
        "k_light": 0.6,
        "sla": 0.02,
        "potential_fruits_per_crown": 10.0,
    }
    model = CropgroStrawberry(40.0, planting_date, soil, cultivar)
    return model.simulate_growth(wth_df)


def main():
    """主函数：运行Python草莓模型。"""
    print("=" * 60)
    print("Python草莓模型模拟器")
    print("=" * 60)
    
    # 查找草莓实验文件
    strawberry_dir = Path("dssat-csm-data-develop/Strawberry")
    srx_files = list(strawberry_dir.glob("*.SRX"))
    
    if not srx_files:
        print("未找到草莓实验文件 (.SRX)")
        return
    
    print(f"找到 {len(srx_files)} 个草莓实验文件:")
    for f in srx_files:
        print(f"  - {f.name}")
    
    # 创建输出目录
    output_dir = Path("python_model_outputs")
    output_dir.mkdir(exist_ok=True)
    
    for srx_file in srx_files:
        print(f"\n处理实验: {srx_file.name}")
        
        try:
            # 解析SRX文件
            planting_date, wsta = parse_srx_file(str(srx_file))
            if planting_date is None or wsta is None:
                print(f"  跳过 {srx_file.name}: 无法解析SRX文件")
                continue
            
            print(f"  种植日期: {planting_date}")
            print(f"  气象站: {wsta}")
            
            # 查找天气文件
            year = planting_date[:4]
            weather_dir = Path("dssat-csm-data-develop/Weather")
            weather_files = list(weather_dir.glob(f"{wsta}{year[2:]}*.WTH"))
            
            if not weather_files:
                print(f"  跳过 {srx_file.name}: 未找到天气文件")
                continue
            
            wth_file = weather_files[0]
            print(f"  天气文件: {wth_file.name}")
            
            # 读取天气数据
            wth_df = read_wth_file(str(wth_file))
            print(f"  天气数据: {len(wth_df)} 天")
            
            # 运行Python模型
            results = run_python_model(wth_df, planting_date)
            
            # 保存结果
            output_file = output_dir / f"{srx_file.stem}_python_results.csv"
            results.to_csv(output_file, index=False)
            
            print(f"  模拟完成: {len(results)} 天")
            print(f"  最终生物量: {results['biomass'].iloc[-1]:.2f} g/plant")
            print(f"  最终叶面积指数: {results['leaf_area_index'].iloc[-1]:.2f}")
            print(f"  最终果实数: {results['fruit_number'].iloc[-1]:.2f}")
            print(f"  结果保存到: {output_file}")
            
        except Exception as e:
            print(f"  处理 {srx_file.name} 时出错: {e}")
    
    print(f"\n所有模拟完成！结果保存在: {output_dir}")


if __name__ == "__main__":
    main() 