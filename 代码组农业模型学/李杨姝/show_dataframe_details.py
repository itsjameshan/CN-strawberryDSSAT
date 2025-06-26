#!/usr/bin/env python3
"""
Script to demonstrate the differences in row counts and data structure 
between Python CROPGRO-Strawberry model and DSSAT Fortran model outputs.
"""

import os
import pandas as pd
from datetime import datetime
import importlib.util
import pathlib
from cropgro_strawberry_implementation import run_example_simulation

# Import the CropgroStrawberry class
impl_path = (pathlib.Path(__file__).resolve().parent / 
             "cropgro-strawberry-implementation.py")
spec = importlib.util.spec_from_file_location(
    "cropgro_strawberry_implementation", impl_path)
impl_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl_module)
CropgroStrawberry = impl_module.CropgroStrawberry


def parse_dssat_date(code: str) -> str:
    """Convert DSSAT YYDDD date code to YYYY-MM-DD string."""
    year = 2000 + int(code[:2])
    doy = int(code[2:])
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")


def read_wth_file(path: str) -> pd.DataFrame:
    """Parse a DSSAT .WTH file into a DataFrame."""
    with open(path) as f:
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("@DATE"))
    header = lines[start].split()
    indices = {h: idx for idx, h in enumerate(header)}
    records = []
    for line in lines[start + 1:]:
        if not line.strip() or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < len(header):
            continue
        code = parts[0]
        date = parse_dssat_date(code)
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
    return pd.DataFrame(records)


def read_fortran_output(exp_dir: str) -> pd.DataFrame:
    """Load PlantGro.OUT produced by DSSAT."""
    pg_path = os.path.join(exp_dir, "PlantGro.OUT")
    if os.path.exists(pg_path):
        with open(pg_path) as f:
            lines = f.readlines()
        header_idx = next(i for i, line in enumerate(lines) if line.startswith("@YEAR"))
        return pd.read_fwf(pg_path, skiprows=header_idx)
    raise FileNotFoundError("No DSSAT PlantGro.OUT found")


def run_python_model(wth_df: pd.DataFrame, planting_date: str):
    """Simulate growth using Python model."""
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
    # Use the strawberry experiment data
    exp_dir = "dssat-csm-data-develop/Strawberry"
    planting_date = "2014-10-09"  # From UFBA1401.SRX
    
    # Read weather data
    weather_dir = os.path.join("dssat-csm-data-develop", "Weather")
    wth_path = os.path.join(weather_dir, "UFBA1401.WTH")
    
    if not os.path.exists(wth_path):
        print(f"Weather file not found: {wth_path}")
        return
    
    wth_df = read_wth_file(wth_path)
    print("=== WEATHER DATA ===")
    print(f"Weather data shape: {wth_df.shape}")
    print(f"Date range: {wth_df['date'].min()} to {wth_df['date'].max()}")
    print(f"Total days in weather file: {len(wth_df)}")
    print()
    
    # Run Python model
    py_df = run_python_model(wth_df, planting_date)
    print("=== PYTHON MODEL OUTPUT ===")
    print(f"Python model shape: {py_df.shape}")
    print(f"Python model columns: {list(py_df.columns)}")
    print(f"Date range: {py_df['date'].min()} to {py_df['date'].max()}")
    print(f"Days after planting range: {py_df['dap'].min()} to {py_df['dap'].max()}")
    print("Sample of first 5 rows:")
    print(py_df[['date', 'dap', 'stage', 'biomass', 'leaf_area_index', 'fruit_biomass']].head())
    print()
    
    # Read DSSAT output if available
    try:
        fort_df = read_fortran_output(exp_dir)
        print("=== DSSAT FORTRAN OUTPUT ===")
        print(f"DSSAT output shape: {fort_df.shape}")
        print(f"DSSAT output columns: {list(fort_df.columns)}")
        if 'DAP' in fort_df.columns:
            print(f"Days after planting range: {fort_df['DAP'].min()} to {fort_df['DAP'].max()}")
        print("Sample of first 5 rows:")
        key_cols = ['YEAR', 'DOY', 'DAP', 'LAID', 'VWAD', 'GWAD'] if all(c in fort_df.columns for c in ['YEAR', 'DOY', 'DAP', 'LAID', 'VWAD', 'GWAD']) else fort_df.columns[:6]
        print(fort_df[key_cols].head())
        print()
        
        print("=== COMPARISON SUMMARY ===")
        print(f"Python model: {py_df.shape[0]} rows × {py_df.shape[1]} columns")
        print(f"DSSAT model:  {fort_df.shape[0]} rows × {fort_df.shape[1]} columns")
        print(f"Row difference: {py_df.shape[0] - fort_df.shape[0]} rows")
        print()
        
        print("=== WHY THE DIFFERENCE? ===")
        print("1. SIMULATION APPROACH:")
        print("   - Python model: Simulates EVERY day from planting to end of weather data")
        print("   - DSSAT model: Only outputs significant growth periods/events")
        print()
        print("2. OUTPUT FREQUENCY:")
        print("   - Python model: Daily output (research/analysis focus)")
        print("   - DSSAT model: Event-driven output (agricultural management focus)")
        print()
        print("3. DATA PURPOSE:")
        print("   - Python model: Complete time series for research analysis")
        print("   - DSSAT model: Key growth stages for farm management decisions")
        
    except FileNotFoundError:
        print("=== DSSAT OUTPUT NOT FOUND ===")
        print("Run DSSAT first to generate PlantGro.OUT for comparison")
        print("Command: python validate_models.py ./dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir dssat-csm-os-develop")

    # 运行模型，获取结果
    model, results, fig = run_example_simulation()
    # 保存为指定csv文件
    results.to_csv('show_dataframe_details.csv', index=False)
    print("模拟结果已保存为 show_dataframe_details.csv")


if __name__ == "__main__":
    main() 