#!/usr/bin/env python3
"""使用列名映射比较Python和DSSAT输出"""

import os
import pandas as pd
from pathlib import Path

def read_dssat_output(file_path: str) -> pd.DataFrame:
    """读取DSSAT输出文件。"""
    if file_path.endswith('.OUT'):
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        header_idx = None
        for i, line in enumerate(lines):
            if line.startswith('@YEAR'):
                header_idx = i
                break
        
        if header_idx is None:
            raise ValueError("未找到表头行")
        
        data_lines = []
        for line in lines[header_idx + 1:]:
            if line.strip() and not line.startswith('*'):
                data_lines.append(line)
        
        if data_lines:
            header = lines[header_idx].strip().split()
            data = []
            for line in data_lines:
                parts = line.strip().split()
                if len(parts) >= len(header):
                    data.append(parts[:len(header)])
            
            df = pd.DataFrame(data, columns=header)
            
            for col in df.columns:
                if col not in ['@YEAR', 'DOY', 'DAS', 'DAP']:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    except:
                        pass
            
            return df
        else:
            return pd.DataFrame()
    else:
        return pd.read_csv(file_path)

def map_columns(py_df: pd.DataFrame, dssat_df: pd.DataFrame):
    """创建Python和DSSAT列之间的映射。"""
    # 定义映射关系
    column_mapping = {
        'biomass': 'CWAD',           # 总生物量
        'leaf_biomass': 'LWAD',      # 叶生物量
        'stem_biomass': 'SWAD',      # 茎生物量
        'root_biomass': 'RWAD',      # 根生物量
        'fruit_biomass': 'GWAD',     # 果实生物量
        'leaf_area_index': 'LAID',   # 叶面积指数
        'fruit_number': 'G#AD',      # 果实数量
        'dap': 'DAP',                # 种植后天数
    }
    
    mapped_data = {}
    
    for py_col, dssat_col in column_mapping.items():
        if py_col in py_df.columns and dssat_col in dssat_df.columns:
            mapped_data[py_col] = {
                'python': py_df[py_col],
                'dssat': dssat_df[dssat_col]
            }
    
    return mapped_data

def compare_mapped_data(mapped_data: dict, experiment_name: str):
    """比较映射后的数据。"""
    print(f"\n实验: {experiment_name}")
    print("=" * 60)
    
    if not mapped_data:
        print("没有找到可比较的列")
        return
    
    print(f"{'变量':<15} {'Python均值':<12} {'DSSAT均值':<12} {'Python最大值':<12} {'DSSAT最大值':<12}")
    print("-" * 70)
    
    for var_name, data in mapped_data.items():
        py_values = data['python']
        dssat_values = data['dssat']
        
        # 确保长度一致
        min_len = min(len(py_values), len(dssat_values))
        py_subset = py_values.iloc[:min_len]
        dssat_subset = dssat_values.iloc[:min_len]
        
        # 计算统计信息
        py_mean = py_subset.mean()
        dssat_mean = dssat_subset.mean()
        py_max = py_subset.max()
        dssat_max = dssat_subset.max()
        
        print(f"{var_name:<15} {py_mean:<12.3f} {dssat_mean:<12.3f} {py_max:<12.3f} {dssat_max:<12.3f}")
    
    # 显示Python特有的信息
    print(f"\nPython模型特有信息:")
    print(f"  模拟天数: {len(py_values)} 天")
    print(f"  最终阶段: {py_df['stage'].iloc[-1] if 'stage' in py_df.columns else 'N/A'}")
    print(f"  热时间累积: {py_df['thermal_time'].iloc[-1] if 'thermal_time' in py_df.columns else 'N/A':.1f} 度日")

def main():
    """主函数。"""
    print("Python vs DSSAT 输出比较 (带映射)")
    print("=" * 60)
    
    # 查找Python输出文件
    python_output_dir = Path("python_model_outputs")
    if not python_output_dir.exists():
        print("未找到Python输出目录")
        return
    
    python_files = list(python_output_dir.glob("*_python_results.csv"))
    if not python_files:
        print("未找到Python输出文件")
        return
    
    # 查找DSSAT输出文件
    dssat_dir = Path("dssat-csm-data-develop/Strawberry")
    dssat_file = dssat_dir / "PlantGro.OUT"
    
    if not dssat_file.exists():
        print("未找到DSSAT输出文件")
        return
    
    print(f"找到 {len(python_files)} 个Python输出文件")
    print(f"找到DSSAT输出文件: {dssat_file.name}")
    
    # 读取DSSAT输出
    dssat_df = read_dssat_output(str(dssat_file))
    print(f"DSSAT输出: {len(dssat_df)} 行, {len(dssat_df.columns)} 列")
    
    # 比较每个实验
    for py_file in python_files:
        experiment_name = py_file.stem.replace('_python_results', '')
        
        try:
            # 读取Python输出
            py_df = pd.read_csv(py_file)
            print(f"\nPython输出: {len(py_df)} 行, {len(py_df.columns)} 列")
            
            # 创建映射
            mapped_data = map_columns(py_df, dssat_df)
            
            # 比较数据
            compare_mapped_data(mapped_data, experiment_name)
            
        except Exception as e:
            print(f"处理 {experiment_name} 时出错: {e}")

if __name__ == "__main__":
    main() 