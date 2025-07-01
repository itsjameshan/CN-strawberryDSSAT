"""Enhanced version of compare_with_fortran.py with detailed difference analysis."""
"""增强版本的 Fortran DSSAT 模型和 Python 版本对比工具，包含详细差异分析。"""

import argparse  # 解析命令行参数
import os  # 文件路径和进程相关操作
import subprocess  # 运行外部程序
from datetime import datetime  # 日期计算

import pandas as pd  # 核心数据结构库
import pandas.testing as pdt  # DataFrame 比较工具

# 从带有连字符文件名的文件导入 CropgroStrawberry 类。
import importlib.util  # 动态导入工具
import pathlib  # 文件系统路径助手

impl_path = (pathlib.Path(__file__).resolve().parent / 
              "cropgro-strawberry-implementation.py")  # 指向实现文件的路径
spec = importlib.util.spec_from_file_location(  # 创建一个指向该文件的模块 spec
    "cropgro_strawberry_implementation", impl_path)  # 模块名和路径
impl_module = importlib.util.module_from_spec(spec)  # 从 spec 获取模块对象
spec.loader.exec_module(impl_module)  # 执行该模块以获得属性
CropgroStrawberry = impl_module.CropgroStrawberry  # 提取类定义


def parse_dssat_date(code: str) -> str:  # decode a YYDDD date
    """将 DSSAT YYDDD 日期码转换为 YYYY-MM-DD 字符串。"""
    year = 2000 + int(code[:2])  # 前两位转换为年份
    doy = int(code[2:])  # 剩下的字符为一年中的天数
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")  # 解析并格式化为 ISO 日期


def parse_srx_file(path: str):  # read planting date and station from experiment
    """从 SRX 文件中提取种植日期和气象站代码。"""
    planting_code = None  # 占位种植日期码
    wsta = None  # 占位气象站代码
    with open(path) as f:  # 打开 SRX 实验文件
        lines = f.readlines()  # 读取所有行到内存中
    for i, line in enumerate(lines):  # examine each line with its index
        if line.startswith("@L ID_FIELD"):  # look for the field section indicator
            if i + 1 < len(lines):  # ensure the next line exists
                parts = lines[i + 1].split()  # split the following line into parts
                if len(parts) >= 3:  # verify there are enough tokens
                    wsta = parts[2]  # capture the weather station code
        if line.startswith("@P PDATE"):  # look for the planting date indicator
            if i + 1 < len(lines):  # ensure the next line exists
                parts = lines[i + 1].split()  # split the following line into parts
                if len(parts) >= 2:  # verify there are enough tokens
                    planting_code = parts[1]  # capture the planting date code
    planting_date = parse_dssat_date(planting_code) if planting_code else None  # 如找到则将代码转为日期字符串
    return planting_date, wsta  # 返回提取的值


def read_wth_file(path: str) -> pd.DataFrame:  # read weather data from .WTH
    """将 DSSAT .WTH 文件解析为 DataFrame。"""
    with open(path) as f:  # 打开气象文件
        lines = f.readlines()  # 读取文件行
    start = next(i for i, l in enumerate(lines) if l.startswith("@DATE"))  # 定位表头所在行
    header = lines[start].split()  # 获取列名
    indices = {h: idx for idx, h in enumerate(header)}  # 列名映射到位置
    records = []  # 用于存储每天记录的列表
    for line in lines[start + 1 :]:  # process each subsequent line
        if not line.strip() or line.startswith("*"):  # skip blank lines and comments
            continue  # ignore lines that have no data
        parts = line.split()  # split the data fields
        code = parts[0]  # YYDDD code
        date = parse_dssat_date(code)  # convert to ISO date
        rec = {  # build a record for this day
            "date": date,  # 日期字符串
            "tmax": float(parts[indices["TMAX"]]),  # 最高温度
            "tmin": float(parts[indices["TMIN"]]),  # 最低温度
            "solar_radiation": float(parts[indices["SRAD"]]),  # 太阳辐射
            "rainfall": float(parts[indices["RAIN"]]) if "RAIN" in indices and len(parts) > indices["RAIN"] else 0.0,  # 降雨量
            "rh": float(parts[indices["RHUM"]]) if "RHUM" in indices and len(parts) > indices["RHUM"] else 70.0,  # 相对湿度
            "wind_speed": float(parts[indices["WIND"]]) if "WIND" in indices and len(parts) > indices["WIND"] else 2.0,  # 风速
        }  # end of record dictionary
        records.append(rec)  # store the day's data
    return pd.DataFrame(records)  # convert list to DataFrame


def run_dssat(srx_path: str, dssat_dir: str):  # invoke the DSSAT executable
    """使用 DSSAT 可执行文件对指定的 SRX 文件运行 DSSAT。"""
    # Use the DSSAT executable directly instead of the run_dssat wrapper
    dssat_exe = "/app/dssat/dscsm048"  # Direct path to DSSAT executable in Docker
    if not os.path.exists(dssat_exe):  # 确认该可执行文件存在
        # Fallback to local path if not in Docker
        dssat_exe = os.path.abspath(os.path.join(dssat_dir, "dscsm048"))
        if not os.path.exists(dssat_exe):
            raise FileNotFoundError(f"DSSAT executable not found at {dssat_exe}")  # 如未找到则抛出异常
    
    # Change to the experiment directory first, then run DSSAT
    # This matches our successful manual approach
    original_dir = os.getcwd()
    try:
        os.chdir(os.path.dirname(srx_path))
        # Run DSSAT with correct syntax: dscsm048 CRGRO048 A FileX
        # CRGRO048 = CROPGRO model for strawberry
        # A = Run all treatments in the specified FileX
        subprocess.run([dssat_exe, "CRGRO048", "A", os.path.basename(srx_path)], check=True)
    finally:
        os.chdir(original_dir)  # Always return to original directory


def read_fortran_output(exp_dir: str) -> pd.DataFrame:  # read DSSAT output files
    """读取 DSSAT 生成的 summary.csv 或 PlantGro.OUT 文件。"""
    summary_path = os.path.join(exp_dir, "summary.csv")  # 检查 CSV 总结文件
    if os.path.exists(summary_path):  # 如果存在则加载 CSV
        return pd.read_csv(summary_path)  # 返回 DataFrame
    pg_path = os.path.join(exp_dir, "PlantGro.OUT")  # 回退到 PlantGro.OUT 文件
    if os.path.exists(pg_path):  # 如果存在则加载定宽文件
        # Find the header line starting with @YEAR
        with open(pg_path) as f:
            lines = f.readlines()
        header_idx = next(i for i, line in enumerate(lines) if line.startswith("@YEAR"))
        # Read from header line onwards
        return pd.read_fwf(pg_path, skiprows=header_idx)  # 返回 DataFrame
    raise FileNotFoundError("No DSSAT output found")  # 如未找到任何输出则抛出异常


def run_python_model(wth_df: pd.DataFrame, planting_date: str):  # simulate growth using Python model
    soil = {"max_root_depth": 50.0, "field_capacity": 200.0, "wilting_point": 50.0}  # 简单土壤参数
    cultivar = {  # 品种特性
        "name": "Generic",  # 品种名称
        "tbase": 4.0,  # 基本温度
        "topt": 22.0,  # 最佳温度
        "tmax_th": 35.0,  # 最大温度阈值
        "rue": 2.5,  # 辐射利用效率
        "k_light": 0.6,  # 光截断系数
        "sla": 0.02,  # 比叶面积
        "potential_fruits_per_crown": 10.0,  # 单株潜在果实数
    }
    model = CropgroStrawberry(40.0, planting_date, soil, cultivar)  # 实例化模型
    return model.simulate_growth(wth_df)  # 运行模拟


def map_python_to_dssat_columns(py_df: pd.DataFrame) -> pd.DataFrame:  # map Python column names to DSSAT names
    """将 Python 模型的列名映射为 DSSAT 列名以便比较。"""
    column_mapping = {
        'dap': 'DAP',                    # 种植后天数 (Days After Planting)
        'leaf_area_index': 'LAID',       # 叶面积指数 (Leaf Area Index)
        'leaf_biomass': 'LWAD',          # 叶生物量 (Leaf Weight/Biomass)
        'stem_biomass': 'SWAD',          # 茎生物量 (Stem Weight/Biomass)
        'fruit_biomass': 'GWAD',         # 果实生物量 (Grain/Fruit Weight/Biomass)
        'root_biomass': 'RWAD',          # 根生物量 (Root Weight/Biomass)
        'biomass': 'VWAD',               # 植物总生物量 (Total Vegetative Weight/Biomass)
        'root_depth': 'RDPD',            # 根深 (Root Depth)
        'fruit_number': 'G#AD',          # 果实数量 (Grain/Fruit Number)
        'water_stress': 'WSPD',          # 水分胁迫 (Water Stress)
    }
    
    # Create a copy and rename columns that exist in both mapping and dataframe
    mapped_df = py_df.copy()
    existing_mappings = {old: new for old, new in column_mapping.items() if old in mapped_df.columns}
    mapped_df = mapped_df.rename(columns=existing_mappings)
    
    print(f"Mapped {len(existing_mappings)} Python columns to DSSAT format: {existing_mappings}")
    return mapped_df


def create_comparison_dataframe(fort_df: pd.DataFrame, py_df: pd.DataFrame, common_cols: list) -> pd.DataFrame:
    """创建详细的比较 DataFrame，包含 DSSAT、Python 和差异列。"""
    min_len = min(len(fort_df), len(py_df))
    fort_subset = fort_df[common_cols].head(min_len)
    py_subset = py_df[common_cols].head(min_len)
    
    # Create comparison dataframe
    comparison_data = {}
    
    # Add index information
    comparison_data['Row'] = range(min_len)
    
    # Add columns for each variable with DSSAT, Python, and difference values
    for col in common_cols:
        dssat_vals = fort_subset[col].values
        python_vals = py_subset[col].values
        
        # DSSAT values
        comparison_data[f'{col}_DSSAT'] = dssat_vals
        
        # Python values  
        comparison_data[f'{col}_Python'] = python_vals
        
        # Absolute difference
        comparison_data[f'{col}_Diff'] = dssat_vals - python_vals
        
        # Percentage difference (handle division by zero)
        pct_diff = []
        for d, p in zip(dssat_vals, python_vals):
            if abs(d) > 1e-10:
                pct_diff.append((d - p) / d * 100)
            else:
                pct_diff.append(0.0 if abs(p) < 1e-10 else float('inf'))
        comparison_data[f'{col}_PctDiff'] = pct_diff
    
    return pd.DataFrame(comparison_data)


def create_summary_statistics(comparison_df: pd.DataFrame, common_cols: list) -> pd.DataFrame:
    """创建汇总统计表，显示每个变量的平均值和差异。"""
    summary_data = []
    
    for col in common_cols:
        dssat_col = f'{col}_DSSAT'
        python_col = f'{col}_Python'
        diff_col = f'{col}_Diff'
        pct_col = f'{col}_PctDiff'
        
        if dssat_col in comparison_df.columns and python_col in comparison_df.columns:
            dssat_mean = comparison_df[dssat_col].mean()
            python_mean = comparison_df[python_col].mean()
            diff_mean = comparison_df[diff_col].mean()
            pct_mean = comparison_df[pct_col].replace([float('inf'), -float('inf')], 0).mean()
            
            # Calculate correlation if possible
            try:
                correlation = comparison_df[dssat_col].corr(comparison_df[python_col])
            except:
                correlation = 0.0
            
            summary_data.append({
                'Variable': col,
                'DSSAT_Mean': dssat_mean,
                'Python_Mean': python_mean,
                'Abs_Diff_Mean': diff_mean,
                'Pct_Diff_Mean': pct_mean,
                'Correlation': correlation,
                'DSSAT_Max': comparison_df[dssat_col].max(),
                'Python_Max': comparison_df[python_col].max(),
                'DSSAT_Min': comparison_df[dssat_col].min(),
                'Python_Min': comparison_df[python_col].min()
            })
    
    return pd.DataFrame(summary_data)


def save_comparison_results(comparison_df: pd.DataFrame, summary_df: pd.DataFrame, output_dir: str):
    """保存比较结果到 CSV 文件。"""
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save detailed comparison
    comparison_file = os.path.join(output_dir, "dssat_python_detailed_comparison.csv")
    comparison_df.to_csv(comparison_file, index=False)
    print(f"📊 Detailed comparison saved to: {comparison_file}")
    
    # Save summary statistics
    summary_file = os.path.join(output_dir, "dssat_python_summary_comparison.csv")
    summary_df.to_csv(summary_file, index=False)
    print(f"📈 Summary comparison saved to: {summary_file}")


def main():  # orchestrate the comparison
    parser = argparse.ArgumentParser(description="Enhanced comparison of DSSAT and Python model outputs")  # 设置命令行解析器
    parser.add_argument("srx", help="Path to DSSAT .SRX file")  # DSSAT .SRX 文件路径
    parser.add_argument("--dssat-dir", default="dssat-csm-os-develop", help="DSSAT installation directory")  # DSSAT 安装目录
    parser.add_argument("--output-dir", default="comparison_results", help="Directory to save comparison results")  # 输出目录
    args = parser.parse_args()  # 解析参数

    print("=== Enhanced DSSAT vs Python Model Comparison ===")

    planting_date, wsta = parse_srx_file(args.srx)  # 从 SRX 提取信息
    if planting_date is None or wsta is None:  # 校验必需数据
        raise ValueError("Could not parse SRX file")  # 如果 SRX 格式有误则终止
    
    print(f"📅 Planting date: {planting_date}")
    print(f"🌍 Weather station: {wsta}")

    print("\n🔄 Running DSSAT simulation...")
    run_dssat(args.srx, args.dssat_dir)  # 生成 Fortran 输出

    exp_dir = os.path.dirname(args.srx)  # 输出文件所在目录
    fort_df = read_fortran_output(exp_dir)  # 加载 DSSAT 结果
    print(f"✅ DSSAT completed: {fort_df.shape}")

    year = planting_date[:4]  # 提取年份以检索天气数据
    weather_dir = os.path.join("dssat-csm-data-develop", "Weather")  # 天气文件根目录
    matches = [f for f in os.listdir(weather_dir) if f.startswith(f"{wsta}{year[2:]}") and f.endswith(".WTH")]  # 查找匹配文件
    if not matches:  # 确保天气文件存在
        raise FileNotFoundError("Weather file not found")  # 若无则报错
    wth_path = os.path.join(weather_dir, matches[0])  # 取第一个匹配文件
    wth_df = read_wth_file(wth_path)  # 加载天气文件到 DataFrame
    print(f"📊 Weather data loaded: {wth_df.shape}")

    print("\n🔄 Running Python model...")
    py_df = run_python_model(wth_df, planting_date)  # 运行 Python 模型
    print(f"✅ Python model completed: {py_df.shape}")
    
    # Map Python columns to DSSAT column names
    py_df_mapped = map_python_to_dssat_columns(py_df)  # 映射列名
    
    # Find common columns between mapped Python output and DSSAT output
    common_cols = [c for c in fort_df.columns if c in py_df_mapped.columns]
    print(f"\n🔍 Found {len(common_cols)} common variables: {common_cols}")
    
    if not common_cols:
        print("❌ No common columns found for comparison")
        return
    
    print("\n📊 Creating detailed comparison...")
    # Create detailed comparison DataFrame
    comparison_df = create_comparison_dataframe(fort_df, py_df_mapped, common_cols)
    print(f"✅ Detailed comparison created: {len(comparison_df)} rows × {len(comparison_df.columns)} columns")
    
    # Create summary statistics
    summary_df = create_summary_statistics(comparison_df, common_cols)
    print(f"✅ Summary statistics created for {len(summary_df)} variables")
    
    # Display results
    print(f"\n=== 📈 SUMMARY STATISTICS ===")
    print(summary_df.round(3))
    
    print(f"\n=== 📋 DETAILED COMPARISON (First 10 rows) ===")
    # Show a subset of columns for readability
    display_cols = ['Row']
    for col in common_cols[:3]:  # Show first 3 variables
        display_cols.extend([f'{col}_DSSAT', f'{col}_Python', f'{col}_Diff', f'{col}_PctDiff'])
    
    if len(display_cols) > 1:
        print(comparison_df[display_cols].head(10))
    
    # Save results to files
    print(f"\n💾 Saving results...")
    save_comparison_results(comparison_df, summary_df, args.output_dir)
    
    print(f"\n=== ✅ COMPARISON COMPLETED ===")
    print(f"📁 Results saved in '{args.output_dir}' directory")
    print(f"📊 Files created:")
    print(f"  - dssat_python_detailed_comparison.csv (Row-by-row comparison)")
    print(f"  - dssat_python_summary_comparison.csv (Variable summary statistics)")


if __name__ == "__main__":  # 作为主程序时运行
    main()  # 启动程序 