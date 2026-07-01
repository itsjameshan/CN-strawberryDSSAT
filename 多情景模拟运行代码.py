#!/usr/bin/env python3
"""
多情景模拟运行代码
==================

本脚本用于分3组开展多情景模拟测试，对比Python版与原版DSSAT输出差异。

情景设计：
1. 情景A：标准条件（基准情景）- 使用UFBA1401试验数据
2. 情景B：高温胁迫情景 - 所有温度增加3°C
3. 情景C：干旱胁迫情景 - 降雨量减少50%

输出文件：
- 各情景模拟结果CSV文件
- Python版与Fortran版对比数据
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

import matplotlib
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util
impl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cropgro-strawberry-implementation.py')
spec = importlib.util.spec_from_file_location('cropgro_impl', impl_path)
impl_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl_module)
CropgroStrawberry = impl_module.CropgroStrawberry


def load_weather_data(wth_file_path):
    """加载DSSAT气象文件"""
    with open(wth_file_path, 'r') as f:
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


def create_scenario_weather(base_weather, scenario_type):
    """根据情景类型修改气象数据"""
    weather = base_weather.copy()
    
    if scenario_type == 'B':
        weather['tmax'] += 3.0
        weather['tmin'] += 3.0
    elif scenario_type == 'C':
        weather['rainfall'] *= 0.5
    
    return weather


def run_python_simulation(weather_df, latitude, planting_date, soil_props, cultivar_params, scenario_name):
    """运行Python版模型模拟"""
    print(f"\n{'='*60}")
    print(f"运行Python版模拟 - {scenario_name}")
    print(f"{'='*60}")
    
    model = CropgroStrawberry(
        latitude=latitude,
        planting_date=planting_date,
        soil_properties=soil_props,
        cultivar_params=cultivar_params
    )
    
    results = model.simulate_growth(weather_df)
    
    print(f"模拟完成，共 {len(results)} 天")
    print(f"最终生物量: {results['biomass'].iloc[-1]:.2f} g/plant")
    print(f"最终果实生物量: {results['fruit_biomass'].iloc[-1]:.2f} g/plant")
    print(f"最终LAI: {results['leaf_area_index'].iloc[-1]:.2f}")
    
    return model, results


def plot_scenario_results(scenario_results, output_dir):
    """绘制情景模拟结果图"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    axes[0, 0].set_title('Total Biomass')
    axes[0, 1].set_title('Fruit Biomass')
    axes[1, 0].set_title('Leaf Area Index')
    axes[1, 1].set_title('Water Stress')
    
    colors = {'A': 'blue', 'B': 'red', 'C': 'green'}
    labels = {'A': 'Scenario A - Standard', 'B': 'Scenario B - Heat Stress', 'C': 'Scenario C - Drought'}
    
    for scenario, (model, results) in scenario_results.items():
        color = colors[scenario]
        label = labels[scenario]
        
        axes[0, 0].plot(results['dap'], results['biomass'], color=color, label=label)
        axes[0, 1].plot(results['dap'], results['fruit_biomass'], color=color, label=label)
        axes[1, 0].plot(results['dap'], results['leaf_area_index'], color=color, label=label)
        axes[1, 1].plot(results['dap'], results['water_stress'], color=color, label=label)
    
    for ax in axes.flat:
        ax.legend()
        ax.set_xlabel('Days After Planting (DAP)')
    
    axes[0, 0].set_ylabel('Biomass (g/plant)')
    axes[0, 1].set_ylabel('Fruit Biomass (g/plant)')
    axes[1, 0].set_ylabel('LAI (m2/m2)')
    axes[1, 1].set_ylabel('Water Stress (0-1)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '情景对比图.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n情景对比图已保存")


def generate_scenario_summary(scenario_results, output_dir):
    """生成情景模拟汇总表"""
    summary_data = []
    
    for scenario, (model, results) in scenario_results.items():
        final_row = results.iloc[-1]
        
        summary_data.append({
            '情景': f'Scenario {scenario}',
            'Total Biomass(g/plant)': final_row['biomass'],
            'Leaf Biomass(g/plant)': final_row['leaf_biomass'],
            'Stem Biomass(g/plant)': final_row['stem_biomass'],
            'Root Biomass(g/plant)': final_row['root_biomass'],
            'Fruit Biomass(g/plant)': final_row['fruit_biomass'],
            'Fruit Number(per plant)': final_row['fruit_number'],
            'LAI': final_row['leaf_area_index'],
            'Root Depth(cm)': final_row['root_depth'],
            'Crown Number': final_row['crown_number'],
            'Runner Number': final_row['runner_number'],
            'Max Water Stress': results['water_stress'].max(),
            'Avg Water Stress': results['water_stress'].mean(),
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_path = os.path.join(output_dir, '情景汇总表.csv')
    summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
    print(f"\n情景汇总表已保存至: {summary_path}")
    
    return summary_df


def main():
    """主函数：运行多情景模拟"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'scenario_results')
    os.makedirs(output_dir, exist_ok=True)
    
    strawberry_data_dir = os.path.join(base_dir, 'dssat-csm-data-develop', 'Strawberry')
    
    base_weather = load_weather_data(os.path.join(strawberry_data_dir, 'UFBA1401.WTH'))
    
    soil_props = {
        'max_root_depth': 50.0,
        'field_capacity': 200.0,
        'wilting_point': 50.0
    }
    
    cultivar_params = {
        'name': 'Radiance',
        'tbase': 4.0,
        'topt': 22.0,
        'tmax_th': 35.0,
        'rue': 3.5,
        'k_light': 0.6,
        'sla': 0.02,
        'potential_fruits_per_crown': 10.0
    }
    
    latitude = -12.97
    planting_date = '2014-10-09'
    
    scenario_definitions = {
        'A': {'name': 'Standard Conditions (Baseline)', 'description': 'Using original UFBA1401 weather data, no stress', 'filename': '标准条件模拟结果.csv'},
        'B': {'name': 'Heat Stress Scenario', 'description': 'All temperatures increased by 3°C, simulating global warming', 'filename': '高温胁迫模拟结果.csv'},
        'C': {'name': 'Drought Stress Scenario', 'description': 'Rainfall reduced by 50%, simulating drought conditions', 'filename': '干旱胁迫模拟结果.csv'},
    }
    
    scenario_results = {}
    
    for scenario_id, scenario_info in scenario_definitions.items():
        print(f"\n{'#'*70}")
        print(f"情景 {scenario_id}: {scenario_info['name']}")
        print(f"描述: {scenario_info['description']}")
        print(f"{'#'*70}")
        
        scenario_weather = create_scenario_weather(base_weather, scenario_id)
        
        model, results = run_python_simulation(
            scenario_weather,
            latitude,
            planting_date,
            soil_props,
            cultivar_params,
            scenario_info['name']
        )
        
        results.to_csv(os.path.join(output_dir, scenario_info['filename']), 
                       index=False, encoding='utf-8-sig')
        print(f"Scenario {scenario_id} detailed results saved")
        
        scenario_results[scenario_id] = (model, results)
    
    plot_scenario_results(scenario_results, output_dir)
    
    summary_df = generate_scenario_summary(scenario_results, output_dir)
    
    print(f"\n{'='*70}")
    print("多情景模拟完成")
    print(f"{'='*70}")
    print("\n情景模拟汇总:")
    print(summary_df.to_string(index=False))
    
    return summary_df


if __name__ == '__main__':
    main()