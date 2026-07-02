"""Validate the Python implementation of CROPGRO-Strawberry against DSSAT."""

import argparse  # parse command line arguments
import os  # interact with the filesystem
import subprocess  # launch external programs
from datetime import datetime  # manipulate date information
from pathlib import Path  # object-oriented filesystem paths
import pandas as pd  # tabular data handling

# Import CropgroStrawberry from the implementation file
import importlib.util  # utilities for dynamic import

impl_path = Path(__file__).resolve().parent / "cropgro-strawberry-implementation.py"  # path to implementation file
spec = importlib.util.spec_from_file_location("cropgro_impl", impl_path)  # module specification from path
impl_module = importlib.util.module_from_spec(spec)  # create module object
spec.loader.exec_module(impl_module)  # execute the module so attributes are available
CropgroStrawberry = impl_module.CropgroStrawberry  # get the class definition


def parse_dssat_date(code: str) -> str:
    """Return ISO date string corresponding to a YYDDD DSSAT code."""
    year = 2000 + int(code[:2])  # DSSAT years are 2000-based
    doy = int(code[2:])  # remaining digits give day of year
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")  # parse and format


def parse_srx_file(path: str):
    """Extract planting date and weather station code from an SRX experiment."""
    planting_code = None  # YYDDD planting date code from the file
    wsta = None  # weather station identifier
    with open(path) as f:  # read the entire SRX file
        lines = f.readlines()
    for i, line in enumerate(lines):  # iterate with index to peek at next line
        if line.startswith("@L ID_FIELD") and i + 1 < len(lines):  # field block
            parts = lines[i + 1].split()  # tokens from next line
            if len(parts) >= 3:
                wsta = parts[2]  # third token stores weather station code
        if line.startswith("@P PDATE") and i + 1 < len(lines):  # planting date block
            parts = lines[i + 1].split()
            if len(parts) >= 2:
                planting_code = parts[1]  # second token is planting date
    planting_date = parse_dssat_date(planting_code) if planting_code else None  # convert to ISO date
    return planting_date, wsta  # return tuple


def read_wth_file(path: str) -> pd.DataFrame:
    """Parse a DSSAT .WTH file into a pandas DataFrame."""
    with open(path) as f:  # open the weather file
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("@DATE"))  # header line index
    header = lines[start].split()  # column names
    indices = {h: idx for idx, h in enumerate(header)}  # map header -> column index
    records = []  # list of daily weather dictionaries
    for line in lines[start + 1 :]:  # process each record line
        if not line.strip() or line.startswith("*"):  # skip blanks and comments
            continue
        parts = line.split()  # split the data fields
        code = parts[0]  # first field is YYDDD date code
        date = parse_dssat_date(code)  # convert to YYYY-MM-DD
        rec = {
            "date": date,
            "tmax": float(parts[indices["TMAX"]]),  # daily max temperature
            "tmin": float(parts[indices["TMIN"]]),  # daily min temperature
            "solar_radiation": float(parts[indices["SRAD"]]),  # radiation MJ/m^2
            "rainfall": float(parts[indices["RAIN"]]) if "RAIN" in indices and len(parts) > indices["RAIN"] else 0.0,  # precipitation
            "rh": float(parts[indices["RHUM"]]) if "RHUM" in indices and len(parts) > indices["RHUM"] else 70.0,  # relative humidity
            "wind_speed": float(parts[indices["WIND"]]) if "WIND" in indices and len(parts) > indices["WIND"] else 2.0,  # wind speed m/s
        }
        records.append(rec)  # store this day's data
    return pd.DataFrame(records)  # assemble DataFrame


def run_dssat(srx_path: str, dssat_dir: str):
    """Run the official DSSAT model using the direct executable."""
    # Use the DSSAT executable directly instead of the problematic run_dssat wrapper
    dssat_exe_locations = [
        Path("/app/dssat/dscsm048"),  # Docker build location (preferred)
        Path(dssat_dir).resolve() / "dscsm048",  # Local build location
    ]
    
    dssat_exe = None
    for location in dssat_exe_locations:
        if location.exists():
            dssat_exe = location
            break
    
    if dssat_exe is None:
        locations_str = '\n  '.join(str(loc) for loc in dssat_exe_locations)
        raise FileNotFoundError(f"DSSAT executable not found in any of these locations:\n  {locations_str}")

    # execute DSSAT from within the experiment directory with correct syntax
    # dscsm048 CRGRO048 A filename.SRX
    subprocess.run(
        [str(dssat_exe), "CRGRO048", "A", os.path.basename(srx_path)],  # correct DSSAT command syntax
        cwd=os.path.dirname(srx_path),  # run in experiment directory
        check=True,  # raise an error if the process fails
    )


def read_fortran_output(exp_dir: str) -> pd.DataFrame:
    """Read DSSAT output files from the experiment directory."""
    summary_path = os.path.join(exp_dir, "summary.csv")  # preferred CSV output
    if os.path.exists(summary_path):  # load if available
        return pd.read_csv(summary_path)
    pg_path = os.path.join(exp_dir, "PlantGro.OUT")  # fallback fixed-width file
    if os.path.exists(pg_path):
        return pd.read_fwf(pg_path, skiprows=4)
    raise FileNotFoundError("No DSSAT output found")  # no recognised output present


def run_python_model(wth_df: pd.DataFrame, planting_date: str) -> pd.DataFrame:
    """Simulate crop growth with the Python implementation."""
    soil = {
        "max_root_depth": 50.0,
        "field_capacity": 200.0,
        "wilting_point": 50.0,
    }  # very simple soil parameters
    cultivar = {
        "name": "Generic",
        "tbase": 4.0,
        "topt": 22.0,
        "tmax_th": 35.0,
        "rue": 2.5,
        "k_light": 0.6,
        "sla": 0.02,
        "potential_fruits_per_crown": 10.0,
    }  # default cultivar description
    model = CropgroStrawberry(40.0, planting_date, soil, cultivar)  # create model instance
    return model.simulate_growth(wth_df)  # run simulation and return DataFrame


def generate_report(fort_df: pd.DataFrame, py_df: pd.DataFrame, tolerance: float) -> str:
    """Create a short report comparing Python and Fortran outputs."""
    common_cols = [c for c in fort_df.columns if c in py_df.columns]  # only check columns present in both
    lines = []  # individual result lines
    max_diff = 0.0  # track worst difference across columns
    for col in common_cols:
        if pd.api.types.is_numeric_dtype(fort_df[col]) and pd.api.types.is_numeric_dtype(py_df[col]):
            min_len = min(len(fort_df), len(py_df))  # ensure lengths match
            diff = (fort_df[col].iloc[:min_len] - py_df[col].iloc[:min_len]).abs().max()
            lines.append(f"{col}: max abs diff {diff:.4f}")
            if diff > max_diff:
                max_diff = diff
    status = "PASSED" if max_diff <= tolerance else "FAILED"  # determine pass/fail
    header = (
        f"Validation {status}. Maximum absolute difference={max_diff:.4f} (tolerance={tolerance})."
    )
    return header + "\n" + "\n".join(lines)  # combine header and column details


def main():
    """Entry point to run the validation workflow."""
    parser = argparse.ArgumentParser(
        description="Validate Python model against DSSAT",
    )  # create argument parser
    parser.add_argument("srx", help="Path to DSSAT .SRX file")  # experiment file
    parser.add_argument(
        "--dssat-dir",
        default="dssat-csm-os-develop",
        help="Directory containing DSSAT build",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1.0,
        help="Acceptable absolute error tolerance",
    )
    parser.add_argument(
        "--report",
        default="validation_report.txt",
        help="File to write validation report",
    )
    args = parser.parse_args()  # parse CLI arguments

    planting_date, wsta = parse_srx_file(args.srx)  # extract settings from SRX
    if planting_date is None or wsta is None:  # verify required data
        raise ValueError("Could not parse SRX file")

    run_dssat(args.srx, args.dssat_dir)  # produce Fortran output

    exp_dir = os.path.dirname(args.srx)  # experiment directory
    fort_df = read_fortran_output(exp_dir)  # load DSSAT results

    year = planting_date[:4]  # search year for weather data
    weather_dir = os.path.join("dssat-csm-data-develop", "Weather")  # location of .WTH files
    matches = [
        f for f in os.listdir(weather_dir)
        if f.startswith(f"{wsta}{year[2:]}") and f.endswith(".WTH")
    ]  # locate matching file
    if not matches:
        raise FileNotFoundError("Weather file not found")
    wth_path = os.path.join(weather_dir, matches[0])  # take first match
    wth_df = read_wth_file(wth_path)  # read weather data

    py_df = run_python_model(wth_df, planting_date)  # run Python model

    report = generate_report(fort_df, py_df, args.tolerance)  # compare outputs
    with open(args.report, "w") as f:  # save report to file
        f.write(report)
    print(report)  # also print to console


if __name__ == "__main__":
    main()
