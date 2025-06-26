#!/usr/bin/env python3
"""运行Python草莓模型验证，跳过DSSAT构建"""

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


def generate_validation_report(py_df: pd.DataFrame, experiment_name: str, report_dir: Path):
    """生成Python模型的验证报告。"""
    report_path = report_dir / f"{experiment_name}_python_validation.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"Python草莓模型验证报告\n")
        f.write(f"实验: {experiment_name}\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"模拟参数:\n")
        f.write(f"  纬度: 40.0°\n")
        f.write(f"  土壤最大根深: 50.0 cm\n")
        f.write(f"  田间持水量: 200.0 mm\n")
        f.write(f"  萎蔫点: 50.0 mm\n")
        f.write(f"  基本温度: 4.0°C\n")
        f.write(f"  最适温度: 22.0°C\n")
        f.write(f"  最大温度阈值: 35.0°C\n")
        f.write(f"  辐射利用效率: 2.5 g/MJ\n")
        f.write(f"  光截断系数: 0.6\n")
        f.write(f"  比叶面积: 0.02 m²/g\n")
        f.write(f"  单株潜在果实数: 10.0\n\n")
        
        f.write(f"模拟结果:\n")
        f.write(f"  模拟天数: {len(py_df)} 天\n")
        f.write(f"  最终生物量: {py_df['biomass'].iloc[-1]:.2f} g/plant\n")
        f.write(f"  最终叶面积指数: {py_df['leaf_area_index'].iloc[-1]:.2f}\n")
        f.write(f"  最终果实数: {py_df['fruit_number'].iloc[-1]:.2f}\n")
        f.write(f"  最终阶段: {py_df['stage'].iloc[-1]}\n")
        f.write(f"  累积热时间: {py_df['thermal_time'].iloc[-1]:.1f} 度日\n\n")
        
        f.write(f"时间序列统计:\n")
        f.write(f"  生物量 - 均值: {py_df['biomass'].mean():.3f}, 最大值: {py_df['biomass'].max():.3f}\n")
        f.write(f"  叶面积指数 - 均值: {py_df['leaf_area_index'].mean():.3f}, 最大值: {py_df['leaf_area_index'].max():.3f}\n")
        f.write(f"  果实数 - 均值: {py_df['fruit_number'].mean():.3f}, 最大值: {py_df['fruit_number'].max():.3f}\n")
        f.write(f"  光合作用 - 均值: {py_df['photosynthesis'].mean():.3f}, 最大值: {py_df['photosynthesis'].max():.3f}\n")
        f.write(f"  蒸腾作用 - 均值: {py_df['transpiration'].mean():.3f}, 最大值: {py_df['transpiration'].max():.3f}\n\n")
        
        f.write(f"物候期进展:\n")
        stages = py_df['stage'].unique()
        for stage in stages:
            first_day = py_df[py_df['stage'] == stage]['dap'].iloc[0]
            f.write(f"  {stage}: 第 {first_day} 天\n")
    
    return report_path


def main():
    """主函数：运行Python草莓模型验证。"""
    print("=" * 60)
    print("Python草莓模型验证系统")
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
    
    # 创建报告目录
    report_dir = Path("python_validation_reports")
    report_dir.mkdir(exist_ok=True)
    
    results_summary = []
    
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
            
            # 生成验证报告
            report_file = generate_validation_report(results, srx_file.stem, report_dir)
            
            print(f"  模拟完成: {len(results)} 天")
            print(f"  最终生物量: {results['biomass'].iloc[-1]:.2f} g/plant")
            print(f"  最终叶面积指数: {results['leaf_area_index'].iloc[-1]:.2f}")
            print(f"  最终果实数: {results['fruit_number'].iloc[-1]:.2f}")
            print(f"  结果保存到: {output_file}")
            print(f"  报告保存到: {report_file}")
            
            # 记录结果摘要
            results_summary.append({
                'experiment': srx_file.stem,
                'days': len(results),
                'final_biomass': results['biomass'].iloc[-1],
                'final_lai': results['leaf_area_index'].iloc[-1],
                'final_fruits': results['fruit_number'].iloc[-1],
                'final_stage': results['stage'].iloc[-1]
            })
            
        except Exception as e:
            print(f"  处理 {srx_file.name} 时出错: {e}")
    
    # 生成总体摘要报告
    summary_file = report_dir / "validation_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("Python草莓模型验证摘要\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"成功验证实验数: {len(results_summary)}\n\n")
        
        f.write("各实验结果:\n")
        f.write("-" * 40 + "\n")
        for result in results_summary:
            f.write(f"{result['experiment']}:\n")
            f.write(f"  模拟天数: {result['days']}\n")
            f.write(f"  最终生物量: {result['final_biomass']:.2f} g/plant\n")
            f.write(f"  最终叶面积指数: {result['final_lai']:.2f}\n")
            f.write(f"  最终果实数: {result['final_fruits']:.2f}\n")
            f.write(f"  最终阶段: {result['final_stage']}\n\n")
    
    print(f"\n所有验证完成！")
    print(f"结果保存在: {output_dir}")
    print(f"报告保存在: {report_dir}")
    print(f"摘要报告: {summary_file}")


if __name__ == "__main__":
    main() 