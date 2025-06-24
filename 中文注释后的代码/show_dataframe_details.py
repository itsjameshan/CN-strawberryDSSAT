#!/usr/bin/env python3
"""
Script to demonstrate the differences in row counts and data structure 
between Python CROPGRO-Strawberry model and DSSAT Fortran model outputs.
"""

import os #用于文件路径操作和检查文件是否存在
import pandas as pd# 用于数据处理和分析
from datetime import datetime#用于日期计算
import importlib.util#用于动态模块加载
import pathlib#用于文件系统路径操作

#  动态导入本地实现的CropgroStrawberry类
impl_path = (pathlib.Path(__file__).resolve().parent / 
             "cropgro-strawberry-implementation.py")#构建实现文件的路径
spec = importlib.util.spec_from_file_location(
    "cropgro_strawberry_implementation", impl_path)#创建模块规范
impl_module = importlib.util.module_from_spec(spec)#创建模块对象
spec.loader.exec_module(impl_module)#执行模块以获取属性
CropgroStrawberry = impl_module.CropgroStrawberry#提取类定义


def parse_dssat_date(code: str) -> str:
    """Convert DSSAT YYDDD date code to YYYY-MM-DD string."""#提取年份部分（YY）并转换为完整年份（2000 + YY）
    doy = int(code[2:])#将年份和天数转换为标准日期格式
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")#datetime.strptime：将年份和天数转换为日期对象。strftime：将日期对象格式化为YYYY-MM-DD字符串。



#解析DSSAT气象文件
def read_wth_file(path: str) -> pd.DataFrame:
    """Parse a DSSAT .WTH file into a DataFrame."""
    with open(path) as f:#打开气象文件
        lines = f.readlines()#读取文件的所有行
    start = next(i for i, l in enumerate(lines) if l.startswith("@DATE"))#找到表头列名
    header = lines[start].split()#提取表头列名。
    indices = {h: idx for idx, h in enumerate(header)}#创建列名到索引的映射
    records = []
    for line in lines[start + 1:]:#逐行解析数据。
        if not line.strip() or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < len(header):
            continue
        code = parts[0]
        date = parse_dssat_date(code)#将日期代码转换为标准日期格式。
        rec = {
            "date": date,
            "tmax": float(parts[indices["TMAX"]]),
            "tmin": float(parts[indices["TMIN"]]),
            "solar_radiation": float(parts[indices["SRAD"]]),
            "rainfall": (float(parts[indices["RAIN"]]) 
                        if "RAIN" in indices and len(parts) > indices["RAIN"] 
                        else 0.0),
            "rh": (float(parts[indices["RHUM"]]) 
                  if "RHUM" in indices and len(parts) > indices["RHUM"] 
                  else 70.0),
            "wind_speed": (float(parts[indices["WIND"]]) 
                          if "WIND" in indices and len(parts) > indices["WIND"] 
                          else 2.0),
        }
        records.append(rec)
    return pd.DataFrame(records)#将解析后的记录转换为DataFrame。


#加载DSSAT输出文件
def read_fortran_output(exp_dir: str) -> pd.DataFrame:
    """Load PlantGro.OUT produced by DSSAT."""
    pg_path = os.path.join(exp_dir, "PlantGro.OUT")#构建DSSAT输出文件的路径。
    if os.path.exists(pg_path):#检查文件是否存在。
        with open(pg_path) as f:
            lines = f.readlines()
        header_idx = next(i for i, line in enumerate(lines) if line.startswith("@YEAR"))
        return pd.read_fwf(pg_path, skiprows=header_idx)#读取固定宽度文件，跳过表头行。
    raise FileNotFoundError("No DSSAT PlantGro.OUT found")


#运行python模型
def run_python_model(wth_df: pd.DataFrame, planting_date: str):
    """Simulate growth using Python model."""
    soil = {"max_root_depth": 50.0, "field_capacity": 200.0, "wilting_point": 50.0}#定义土壤和品种参数
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
    model = CropgroStrawberry(40.0, planting_date, soil, cultivar)#实例化Python模型。
    return model.simulate_growth(wth_df)#运行模型，传入气象数据，返回模拟结果。


#主函数
def main():
    # 主函数，协调整个比较过程
    #定义实验目录和种植日期
    exp_dir = "dssat-csm-data-develop/Strawberry"
    planting_date = "2014-10-09"  # 从 UFBA1401.SRX 获取
    
    # 定义气象目录和文件路径
    weather_dir = os.path.join("dssat-csm-data-develop", "Weather")
    wth_path = os.path.join(weather_dir, "UFBA1401.WTH")

   # 检查气象文件是否存在
    if not os.path.exists(wth_path):
        print(f"Weather file not found: {wth_path}")
        return
    
    #读取气象数据
    wth_df = read_wth_file(wth_path)
    print("=== WEATHER DATA ===")#气象数据
    print(f"Weather data shape: {wth_df.shape}")#气象数据形状
    print(f"Date range: {wth_df['date'].min()} to {wth_df['date'].max()}")#日期范围
    print(f"Total days in weather file: {len(wth_df)}")#气象文件中的总天数
    print()
    
    # 运行python模型
    py_df = run_python_model(wth_df, planting_date)
    print("=== PYTHON MODEL OUTPUT ===")#python模型输出
    print(f"Python model shape: {py_df.shape}")#Python模型形状
    print(f"Python model columns: {list(py_df.columns)}")#Python模型列
    print(f"Date range: {py_df['date'].min()} to {py_df['date'].max()}")#日期范围
    print(f"Days after planting range: {py_df['dap'].min()} to {py_df['dap'].max()}")#种植后天数范围
    print("Sample of first 5 rows:")#
    print(py_df[['date', 'dap', 'stage', 前5行的样本'biomass', 'leaf_area_index', 'fruit_biomass']].head())
    print()
    
    # 尝试读取DSSAT输出
    try:
        fort_df = read_fortran_output(exp_dir)
        print("=== DSSAT FORTRAN OUTPUT ===")#DSSAT Fortran输出 
        print(f"DSSAT output shape: {fort_df.shape}")#DSSAT输出形状
        print(f"DSSAT output columns: {list(fort_df.columns)}")#DSSAT输出列
        if 'DAP' in fort_df.columns:
            print(f"Days after planting range: {fort_df['DAP'].min()} to {fort_df['DAP'].max()}")#种植后天数范围
        print("Sample of first 5 rows:")#前5行的样本
        key_cols = ['YEAR', 'DOY', 'DAP', 'LAID', 'VWAD', 'GWAD'] if all(c in fort_df.columns for c in ['YEAR', 'DOY', 'DAP', 'LAID', 'VWAD', 'GWAD']) else fort_df.columns[:6]
        print(fort_df[key_cols].head())
        print()
        
#打印比较总结 
      print("=== COMPARISON SUMMARY ===")
      #打印Python模型的输出形状
        print(f"Python model: {py_df.shape[0]} rows × {py_df.shape[1]} columns")
        #打印DSSAT模型的输出形状
        print(f"DSSAT model:  {fort_df.shape[0]} rows × {fort_df.shape[1]} columns")
        #打印两个模型行数的差异
        print(f"Row difference: {py_df.shape[0] - fort_df.shape[0]} rows")
        print()
        
        print("=== WHY THE DIFFERENCE? ===")#打印差异原因的标题
        print("1. SIMULATION APPROACH:")#打印第一个原因的标题
        print("   - Python model: Simulates EVERY day from planting to end of weather data")#解释Python模型的模拟方法
        print("   - DSSAT model: Only outputs significant growth periods/events")#解释DSSAT模型的模拟方法
        print()
        print("2. OUTPUT FREQUENCY:")#打印第二个原因标题
        print("   - Python model: Daily output (research/analysis focus)")#解释Python模型的输出频率
        print("   - DSSAT model: Event-driven output (agricultural management focus)")#解释DSSAT模型的输出频率
        print()
        print("3. DATA PURPOSE:")# 打印第三个原因的标题
        print("   - Python model: Complete time series for research analysis")#解释Python模型的数据用途
        print("   - DSSAT model: Key growth stages for farm management decisions")# 解释DSSAT模型的数据用途
        
    except FileNotFoundError:#捕获文件找不到异常
        print("=== DSSAT OUTPUT NOT FOUND ===")#打印标题，表明DSSAT输出文件未找到
        print("Run DSSAT first to generate PlantGro.OUT for comparison")#提示用户先运行DSSAT模型以生成PlantGro.OUT文件，以便进行比较
        print("Command: python validate_models.py ./dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir dssat-csm-os-develop")#提供运行DSSAT模型的具体命令，包括脚本名称、实验文件路径和DSSAT安装目录


#调用主函数
if __name__ == "__main__":
    main() 