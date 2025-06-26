#!/usr/bin/env python3
"""比较Python模型输出和现有的DSSAT输出文件"""

import os
import pandas as pd
from pathlib import Path

def read_dssat_output(file_path: str) -> pd.DataFrame:
    """读取DSSAT输出文件。"""
    if file_path.endswith('.OUT'):
        # 读取PlantGro.OUT文件
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # 找到表头行
        header_idx = None
        for i, line in enumerate(lines):
            if line.startswith('@YEAR'):
                header_idx = i
                break
        
        if header_idx is None:
            raise ValueError("未找到表头行")
        
        # 读取数据
        data_lines = []
        for line in lines[header_idx + 1:]:
            if line.strip() and not line.startswith('*'):
                data_lines.append(line)
        
        # 创建DataFrame
        if data_lines:
            # 解析表头
            header = lines[header_idx].strip().split()
            # 解析数据
            data = []
            for line in data_lines:
                parts = line.strip().split()
                if len(parts) >= len(header):
                    data.append(parts[:len(header)])
            
            df = pd.DataFrame(data, columns=header)
            
            # 转换数值列
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

def compare_outputs(python_file: str, dssat_file: str, experiment_name: str):
    """比较Python和DSSAT输出。"""
    print(f"\n比较实验: {experiment_name}")
    print("=" * 50)
    
    try:
        # 读取Python输出
        py_df = pd.read_csv(python_file)
        print(f"Python输出: {len(py_df)} 行, {len(py_df.columns)} 列")
        
        # 读取DSSAT输出
        dssat_df = read_dssat_output(dssat_file)
        print(f"DSSAT输出: {len(dssat_df)} 行, {len(dssat_df.columns)} 列")
        
        # 显示列名
        print(f"\nPython列名: {list(py_df.columns)}")
        print(f"DSSAT列名: {list(dssat_df.columns)}")
        
        # 查找共同列
        common_cols = []
        for col in py_df.columns:
            if col in dssat_df.columns:
                common_cols.append(col)
        
        print(f"\n共同列: {common_cols}")
        
        if not common_cols:
            print("没有找到共同列，无法进行数值比较")
            return
        
        # 比较共同列
        print("\n数值比较:")
        print("-" * 30)
        
        for col in common_cols:
            if pd.api.types.is_numeric_dtype(py_df[col]) and pd.api.types.is_numeric_dtype(dssat_df[col]):
                # 确保长度一致
                min_len = min(len(py_df), len(dssat_df))
                
                py_values = py_df[col].iloc[:min_len]
                dssat_values = dssat_df[col].iloc[:min_len]
                
                # 计算统计信息
                py_mean = py_values.mean()
                dssat_mean = dssat_values.mean()
                py_max = py_values.max()
                dssat_max = dssat_values.max()
                
                print(f"{col:15}: Python均值={py_mean:8.3f}, DSSAT均值={dssat_mean:8.3f}")
                print(f"{'':15}  Python最大值={py_max:8.3f}, DSSAT最大值={dssat_max:8.3f}")
        
        # 显示Python模型的最终状态
        print(f"\nPython模型最终状态:")
        print(f"  最终生物量: {py_df['biomass'].iloc[-1]:.2f} g/plant")
        print(f"  最终叶面积指数: {py_df['leaf_area_index'].iloc[-1]:.2f}")
        print(f"  最终果实数: {py_df['fruit_number'].iloc[-1]:.2f}")
        print(f"  最终阶段: {py_df['stage'].iloc[-1]}")
        
    except Exception as e:
        print(f"比较时出错: {e}")

def main():
    """主函数。"""
    print("Python vs DSSAT 输出比较")
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
    dssat_files = list(dssat_dir.glob("PlantGro.OUT"))
    
    print(f"找到 {len(python_files)} 个Python输出文件")
    print(f"找到 {len(dssat_files)} 个DSSAT输出文件")
    
    # 比较每个实验
    for py_file in python_files:
        experiment_name = py_file.stem.replace('_python_results', '')
        
        # 查找对应的DSSAT文件
        dssat_file = dssat_dir / "PlantGro.OUT"
        
        if dssat_file.exists():
            compare_outputs(str(py_file), str(dssat_file), experiment_name)
        else:
            print(f"\n跳过 {experiment_name}: 未找到对应的DSSAT输出文件")

if __name__ == "__main__":
    main() 