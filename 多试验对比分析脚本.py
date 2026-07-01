#!/usr/bin/env python3
"""
多试验对比分析脚本
==================

本脚本用于对比Python版与原版DSSAT（Fortran）在多个草莓试验中的输出差异。

支持的试验：
- UFBA1401: 巴西萨尔瓦多 2014年试验
- UFBA1601: 巴西萨尔瓦多 2016年试验
- UFBA1701: 巴西萨尔瓦多 2017年试验
- UFWM1401: 美国佛罗里达州 2014年试验

输出：
- 各试验详细对比数据
- 汇总对比表（Excel格式）
- 差异分析报告
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util
impl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cropgro-strawberry-implementation.py')
spec = importlib.util.spec_from_file_location('cropgro_impl', impl_path)
impl_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl_module)
CropgroStrawberry = impl_module.CropgroStrawberry


EXPERIMENTS = {
    'UFBA1401': {
        'name': '巴西萨尔瓦多 2014年试验',
        'latitude': -12.97,
        'planting_date': '2014-10-09',
        'wth_file': 'UFBA1401.WTH',
        'srx_file': 'UFBA1401.SRX',
    },
    'UFBA1601': {
        'name': '巴西萨尔瓦多 2016年试验',
        'latitude': -12.97,
        'planting_date': '2016-10-09',
        'wth_file': 'UFBA1601.WTH',
        'srx_file': 'UFBA1601.SRX',
    },
    'UFBA1701': {
        'name': '巴西萨尔瓦多 2017年试验',
        'latitude': -12.97,
        'planting_date': '2017-10-09',
        'wth_file': 'UFBA1701.WTH',
        'srx_file': 'UFBA1701.SRX',
    },
    'UFWM1401': {
        'name': '美国佛罗里达州 2014年试验',
        'latitude': 28.12,
        'planting_date': '2014-10-01',
        'wth_file': 'UFWM1401.WTH',
        'srx_file': 'UFWM1401.SRX',
    },
}


def load_weather_data(data_dir, wth_file):
    """加载DSSAT气象文件"""
    wth_path = os.path.join(data_dir, wth_file)
    with open(wth_path, 'r') as f:
        lines = f.readlines()
    
    start_idx = next(i for i, line in enumerate(lines) if line.startswith('@DATE'))
    header = lines[start_idx].split()
    
    col_indices = {}
    for col in ['TMAX', 'TMIN', 'SRAD', 'RAIN', 'RHUM', 'WIND']:
        if col in header:
            col_indices[col] = header.index(col)
    
    data = []
    for line in lines[start_idx+1:]:
        if not line.strip() or line.startswith('*'):
            continue
        parts = line.split()
        year = 2000 + int(parts[0][:2])
        doy = int(parts[0][2:])
        date = datetime(year, 1, 1) + timedelta(days=doy-1)
        
        def get_value(col_name, default):
            if col_name in col_indices and col_indices[col_name] < len(parts):
                val = parts[col_indices[col_name]]
                if val.strip() != '':
                    return float(val)
            return default
        
        row = {
            'date': date.strftime('%Y-%m-%d'),
            'tmax': get_value('TMAX', 25.0),
            'tmin': get_value('TMIN', 15.0),
            'solar_radiation': get_value('SRAD', 15.0),
            'rainfall': get_value('RAIN', 0.0),
            'rh': get_value('RHUM', 70.0),
            'wind_speed': get_value('WIND', 2.0),
        }
        data.append(row)
    
    return pd.DataFrame(data)


def load_fortran_output(data_dir):
    """加载Fortran版DSSAT输出"""
    pg_path = os.path.join(data_dir, 'PlantGro.OUT')
    
    with open(pg_path, 'r') as f:
        lines = f.readlines()
    
    start_idx = None
    for i, line in enumerate(lines):
        if line.startswith('@YEAR'):
            start_idx = i
            break
    
    if start_idx is None:
        return None
    
    header = lines[start_idx].split()
    
    data = []
    for line in lines[start_idx+1:]:
        if not line.strip() or line.startswith('*') or line.startswith('!'):
            continue
        parts = line.split()
        if len(parts) < len(header):
            continue
        
        row = {}
        for i, col in enumerate(header):
            if i < len(parts):
                try:
                    row[col] = float(parts[i])
                except ValueError:
                    row[col] = parts[i]
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    return df


def run_python_model(weather_df, latitude, planting_date):
    """运行Python版模型"""
    soil_props = {
        'max_root_depth': 50.0,
        'field_capacity': 200.0,
        'wilting_point': 50.0
    }
    
    cultivar_params = {
        'name': 'Generic',
        'tbase': 4.0,
        'topt': 22.0,
        'tmax_th': 35.0,
        'rue': 2.5,
        'k_light': 0.6,
        'sla': 0.02,
        'potential_fruits_per_crown': 10.0
    }
    
    model = CropgroStrawberry(
        latitude=latitude,
        planting_date=planting_date,
        soil_properties=soil_props,
        cultivar_params=cultivar_params
    )
    
    results = model.simulate_growth(weather_df)
    
    return model, results


def compare_results(fort_df, py_df, experiment_name):
    """对比Fortran和Python结果"""
    comparison = {
        'experiment': experiment_name,
        'fortran_days': len(fort_df),
        'python_days': len(py_df),
    }
    
    column_mapping = {
        'LAID': 'leaf_area_index',
        'LWAD': 'leaf_biomass',
        'SWAD': 'stem_biomass',
        'RWAD': 'root_biomass',
        'GWAD': 'fruit_biomass',
        'VWAD': 'biomass',
    }
    
    for fort_col, py_col in column_mapping.items():
        if fort_col in fort_df.columns and py_col in py_df.columns:
            fort_values = fort_df[fort_col].values[:min(len(fort_df), len(py_df))]
            py_values = py_df[py_col].values[:min(len(fort_df), len(py_df))]
            
            abs_diff = np.abs(fort_values - py_values)
            rel_diff = np.abs(fort_values - py_values) / (np.abs(fort_values) + 1e-10)
            
            comparison[f'{fort_col}_fortran_mean'] = np.mean(fort_values)
            comparison[f'{fort_col}_python_mean'] = np.mean(py_values)
            comparison[f'{fort_col}_max_abs_diff'] = np.max(abs_diff)
            comparison[f'{fort_col}_max_rel_diff'] = np.max(rel_diff)
            comparison[f'{fort_col}_mean_abs_diff'] = np.mean(abs_diff)
            comparison[f'{fort_col}_mean_rel_diff'] = np.mean(rel_diff)
    
    return comparison


def main():
    """主函数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'dssat-csm-data-develop', 'Strawberry')
    output_dir = os.path.join(base_dir, 'comparison_results')
    os.makedirs(output_dir, exist_ok=True)
    
    all_comparisons = []
    
    print(f"{'='*70}")
    print("多试验对比分析 - Python版 vs Fortran版")
    print(f"{'='*70}")
    
    for exp_id, exp_info in EXPERIMENTS.items():
        print(f"\n{'#'*70}")
        print(f"试验: {exp_id} - {exp_info['name']}")
        print(f"{'#'*70}")
        
        weather_df = load_weather_data(data_dir, exp_info['wth_file'])
        print(f"气象数据: {len(weather_df)} 天")
        
        fort_df = load_fortran_output(data_dir)
        if fort_df is not None:
            print(f"Fortran输出: {len(fort_df)} 天")
        else:
            print("⚠️  未找到Fortran输出文件")
            continue
        
        py_model, py_df = run_python_model(
            weather_df, 
            exp_info['latitude'], 
            exp_info['planting_date']
        )
        print(f"Python模拟: {len(py_df)} 天")
        
        comparison = compare_results(fort_df, py_df, exp_id)
        all_comparisons.append(comparison)
        
        print(f"\n对比结果:")
        for key, value in comparison.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")
    
    comparison_df = pd.DataFrame(all_comparisons)
    
    excel_path = os.path.join(output_dir, '输出结果对比表.xlsx')
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        comparison_df.to_excel(writer, sheet_name='对比汇总', index=False)
        
        for exp_id in EXPERIMENTS.keys():
            exp_comparison = comparison_df[comparison_df['experiment'] == exp_id]
            exp_comparison.to_excel(writer, sheet_name=exp_id, index=False)
    
    print(f"\n{'='*70}")
    print(f"对比表已保存至: {excel_path}")
    print(f"{'='*70}")
    
    return comparison_df


if __name__ == '__main__':
    main()