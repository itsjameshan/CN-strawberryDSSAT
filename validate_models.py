import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path
import pandas as pd

# Import CropgroStrawberry from the implementation file
import importlib.util

impl_path = Path(__file__).resolve().parent / "cropgro-strawberry-implementation.py"
spec = importlib.util.spec_from_file_location("cropgro_impl", impl_path)
impl_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl_module)
CropgroStrawberry = impl_module.CropgroStrawberry


def parse_dssat_date(code: str) -> str:
    """Convert DSSAT YYDDD date code to YYYY-MM-DD."""
    year = 2000 + int(code[:2])
    doy = int(code[2:])
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")


def parse_srx_file(path: str):
    """Return planting date and weather station from an SRX file."""
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
    """Load a DSSAT .WTH weather file."""
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
            "tmax": float(parts[indices.get("TMAX")]),
            "tmin": float(parts[indices.get("TMIN")]),
            "solar_radiation": float(parts[indices.get("SRAD")]),
            "rainfall": float(parts[indices.get("RAIN")]) if "RAIN" in indices else 0.0,
            "rh": float(parts[indices.get("RHUM")]) if "RHUM" in indices else 70.0,
            "wind_speed": float(parts[indices.get("WIND")]) if "WIND" in indices else 2.0,
        }
        records.append(rec)
    return pd.DataFrame(records)


def run_dssat(srx_path: str, dssat_dir: str):
    """Execute the DSSAT binary using run_dssat."""
    util = Path(dssat_dir) / "Utilities" / "run_dssat"
    if not util.exists():
        raise FileNotFoundError(f"run_dssat not found at {util}")
    subprocess.run([str(util), os.path.basename(srx_path)], cwd=os.path.dirname(srx_path), check=True)


def read_fortran_output(exp_dir: str) -> pd.DataFrame:
    """Load DSSAT output from summary.csv or PlantGro.OUT."""
    summary_path = os.path.join(exp_dir, "summary.csv")
    if os.path.exists(summary_path):
        return pd.read_csv(summary_path)
    pg_path = os.path.join(exp_dir, "PlantGro.OUT")
    if os.path.exists(pg_path):
        return pd.read_fwf(pg_path, skiprows=4)
    raise FileNotFoundError("No DSSAT output found")


def run_python_model(wth_df: pd.DataFrame, planting_date: str) -> pd.DataFrame:
    """Run the Python implementation using basic soil and cultivar parameters."""
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


def generate_report(fort_df: pd.DataFrame, py_df: pd.DataFrame, tolerance: float) -> str:
    """Return a text report summarising differences between outputs."""
    common_cols = [c for c in fort_df.columns if c in py_df.columns]
    lines = []
    max_diff = 0.0
    for col in common_cols:
        if pd.api.types.is_numeric_dtype(fort_df[col]) and pd.api.types.is_numeric_dtype(py_df[col]):
            min_len = min(len(fort_df), len(py_df))
            diff = (fort_df[col].iloc[:min_len] - py_df[col].iloc[:min_len]).abs().max()
            lines.append(f"{col}: max abs diff {diff:.4f}")
            if diff > max_diff:
                max_diff = diff
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

    run_dssat(args.srx, args.dssat_dir)

    exp_dir = os.path.dirname(args.srx)
    fort_df = read_fortran_output(exp_dir)

    year = planting_date[:4]
    weather_dir = os.path.join("dssat-csm-data-develop", "Weather")
    matches = [f for f in os.listdir(weather_dir) if f.startswith(f"{wsta}{year[2:]}") and f.endswith(".WTH")]
    if not matches:
        raise FileNotFoundError("Weather file not found")
    wth_path = os.path.join(weather_dir, matches[0])
    wth_df = read_wth_file(wth_path)

    py_df = run_python_model(wth_df, planting_date)

    report = generate_report(fort_df, py_df, args.tolerance)
    with open(args.report, "w") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()
