"""Validate the Python implementation of CROPGRO-Strawberry against DSSAT."""

import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path
import pandas as pd

import importlib.util

impl_path = Path(__file__).resolve().parent / "cropgro-strawberry-implementation.py"
spec = importlib.util.spec_from_file_location("cropgro_impl", impl_path)
impl_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl_module)
CropgroStrawberry = impl_module.CropgroStrawberry


COLUMN_MAPPING = {
    'LAID': 'leaf_area_index',
    'LWAD': 'leaf_biomass',
    'SWAD': 'stem_biomass',
    'RWAD': 'root_biomass',
    'GWAD': 'fruit_biomass',
    'VWAD': 'biomass',
}

FORT_TO_PY_UNITS = {
    'LAID': 1.0,
    'LWAD': 0.02,
    'SWAD': 0.02,
    'RWAD': 0.02,
    'GWAD': 0.02,
    'VWAD': 0.02,
}


def parse_dssat_date(code: str) -> str:
    year = 2000 + int(code[:2])
    doy = int(code[2:])
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")


def parse_srx_file(path: str):
    planting_code = None
    wsta = None
    with open(path) as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith("@L ID_FIELD") and i + 1 < len(lines):
            parts = lines[i + 1].split()
            if len(parts) >= 3:
                wsta = parts[2]
        if line.startswith("@P PDATE") and i + 1 < len(lines):
            parts = lines[i + 1].split()
            if len(parts) >= 2:
                planting_code = parts[1]
    planting_date = parse_dssat_date(planting_code) if planting_code else None
    return planting_date, wsta


def read_wth_file(path: str) -> pd.DataFrame:
    with open(path) as f:
        lines = f.readlines()
    
    latitude = 27.760
    for line in lines:
        if line.startswith("@ INSI"):
            header_line = line
            if lines.index(line) + 1 < len(lines):
                data_line = lines[lines.index(line) + 1]
                parts = data_line.split()
                if len(parts) >= 2:
                    latitude = float(parts[1])
            break
    
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
    
    df = pd.DataFrame(records)
    df.attrs['latitude'] = latitude
    return df


def run_dssat(srx_path: str, dssat_dir: str):
    dssat_exe_locations = [
        Path("/app/dssat/dscsm048"),
        Path(dssat_dir).resolve() / "dscsm048",
    ]
    
    dssat_exe = None
    for location in dssat_exe_locations:
        if location.exists():
            dssat_exe = location
            break
    
    if dssat_exe is None:
        print("Warning: DSSAT executable not found, using existing output")
        return
    
    subprocess.run(
        [str(dssat_exe), "CRGRO048", "A", os.path.basename(srx_path)],
        cwd=os.path.dirname(srx_path),
        check=True,
    )


def read_fortran_output(exp_dir: str) -> pd.DataFrame:
    summary_path = os.path.join(exp_dir, "summary.csv")
    if os.path.exists(summary_path):
        return pd.read_csv(summary_path)
    pg_path = os.path.join(exp_dir, "PlantGro.OUT")
    if os.path.exists(pg_path):
        with open(pg_path, 'r') as f:
            lines = f.readlines()
        
        header_line = None
        start_data_idx = None
        for i, line in enumerate(lines):
            if line.startswith('@YEAR'):
                header_line = line.strip()
                start_data_idx = i + 1
                break
        
        if header_line is None or start_data_idx is None:
            raise FileNotFoundError("Could not find header in PlantGro.OUT")
        
        headers = header_line.split()
        
        data = []
        for line in lines[start_data_idx:]:
            if not line.strip() or line.startswith('*') or line.startswith('!'):
                continue
            
            values = []
            remaining = line
            for _ in headers:
                remaining = remaining.lstrip()
                if not remaining:
                    values.append('')
                    continue
                if ' ' in remaining:
                    idx = remaining.index(' ')
                    values.append(remaining[:idx])
                    remaining = remaining[idx:]
                else:
                    values.append(remaining)
                    remaining = ''
            
            row = {}
            for i, col in enumerate(headers):
                if i < len(values):
                    try:
                        row[col] = float(values[i])
                    except ValueError:
                        row[col] = values[i]
            data.append(row)
        
        df = pd.DataFrame(data)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except:
                pass
        return df
    
    raise FileNotFoundError("No DSSAT output found")


def run_python_model(wth_df: pd.DataFrame, planting_date: str, latitude: float) -> pd.DataFrame:
    soil = {
        "max_root_depth": 50.0,
        "field_capacity": 200.0,
        "wilting_point": 50.0,
    }
    cultivar = {
        "name": "Radiance",
        "tbase": 4.0,
        "topt": 22.0,
        "tmax_th": 35.0,
        "rue": 3.5,
        "k_light": 0.6,
        "sla": 0.02,
        "potential_fruits_per_crown": 10.0,
    }
    model = CropgroStrawberry(latitude, planting_date, soil, cultivar)
    return model.simulate_growth(wth_df)


def generate_report(fort_df: pd.DataFrame, py_df: pd.DataFrame, tolerance: float) -> str:
    lines = []
    max_diff = 0.0
    
    fort_dap = fort_df.get('DAP', fort_df.get('dap', np.arange(len(fort_df))))
    py_dap = py_df.get('dap', py_df.get('DAP', np.arange(len(py_df))))
    
    common_daps = np.intersect1d(fort_dap, py_dap)
    
    lines.append(f"匹配到 {len(common_daps)} 个共同的种植后天数(DAP)")
    
    for fort_col, py_col in COLUMN_MAPPING.items():
        if fort_col in fort_df.columns and py_col in py_df.columns:
            fort_values = []
            py_values = []
            
            for dap in common_daps:
                fort_idx = np.where(fort_dap == dap)[0]
                py_idx = np.where(py_dap == dap)[0]
                if len(fort_idx) > 0 and len(py_idx) > 0:
                    fort_values.append(fort_df[fort_col].values[fort_idx[0]])
                    py_values.append(py_df[py_col].values[py_idx[0]])
            
            if len(fort_values) == 0:
                continue
            
            fort_values = np.array(fort_values)
            py_values = np.array(py_values)
            
            unit_factor = FORT_TO_PY_UNITS.get(fort_col, 1.0)
            fort_values_converted = fort_values * unit_factor
            
            abs_diff = np.abs(fort_values_converted - py_values)
            rel_diff = np.abs(fort_values_converted - py_values) / (np.abs(fort_values_converted) + 1e-10)
            
            max_abs = np.max(abs_diff)
            max_rel = np.max(rel_diff)
            mean_abs = np.mean(abs_diff)
            mean_rel = np.mean(rel_diff)
            
            lines.append(f"{fort_col}({py_col}): max_abs_diff={max_abs:.4f}, max_rel_diff={max_rel:.4f}, mean_abs_diff={mean_abs:.4f}, mean_rel_diff={mean_rel:.4f}")
            
            if max_abs > max_diff:
                max_diff = max_abs
    
    status = "PASSED" if max_diff <= tolerance else "FAILED"
    header = f"Validation {status}. Maximum absolute difference={max_diff:.4f} (tolerance={tolerance})."
    return header + "\n" + "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate Python model against DSSAT")
    parser.add_argument("srx", help="Path to DSSAT .SRX file")
    parser.add_argument("--dssat-dir", default="dssat-csm-os-develop", help="Directory containing DSSAT build")
    parser.add_argument("--tolerance", type=float, default=1.0, help="Acceptable absolute error tolerance")
    parser.add_argument("--report", default="validation_report.txt", help="File to write validation report")
    args = parser.parse_args()

    planting_date, wsta = parse_srx_file(args.srx)
    if planting_date is None or wsta is None:
        raise ValueError("Could not parse SRX file")

    exp_dir = os.path.dirname(args.srx)
    
    try:
        run_dssat(args.srx, args.dssat_dir)
    except Exception as e:
        print(f"Warning: Could not run DSSAT executable: {e}")
    
    fort_df = read_fortran_output(exp_dir)

    year = planting_date[:4]
    weather_dir = os.path.join("dssat-csm-data-develop", "Weather")
    matches = [f for f in os.listdir(weather_dir) if f.startswith(f"{wsta}{year[2:]}") and f.endswith(".WTH")]
    if not matches:
        strawberry_dir = os.path.join("dssat-csm-data-develop", "Strawberry")
        matches = [f for f in os.listdir(strawberry_dir) if f.startswith(f"{wsta}{year[2:]}") and f.endswith(".WTH")]
    
    if not matches:
        raise FileNotFoundError("Weather file not found")
    
    wth_path = os.path.join(strawberry_dir if 'strawberry_dir' in dir() else weather_dir, matches[0])
    wth_df = read_wth_file(wth_path)
    
    latitude = wth_df.attrs.get('latitude', 27.760)

    max_dap = int(fort_df['DAP'].max()) if 'DAP' in fort_df.columns else 85
    wth_df = wth_df.head(max_dap + 1)

    py_df = run_python_model(wth_df, planting_date, latitude)

    report = generate_report(fort_df, py_df, args.tolerance)
    with open(args.report, "w") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    import numpy as np
    main()