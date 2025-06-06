"""Compare outputs from the Fortran DSSAT model with the Python version."""

import argparse  # parsing command line options
import os  # file path and process utilities
import subprocess  # running external programs
from datetime import datetime  # date computations

import pandas as pd  # core data structure library
import pandas.testing as pdt  # dataframe comparison helpers

# Import the CropgroStrawberry class from a file with a hyphen in its name.
import importlib.util  # utilities for dynamic imports
import pathlib  # filesystem path helpers

impl_path = pathlib.Path(__file__).resolve().parent / "cropgro-strawberry-implementation.py"  # path to implementation
spec = importlib.util.spec_from_file_location(  # create a module spec pointing at the file
    "cropgro_strawberry_implementation", impl_path  # module name and path
)  # end of spec arguments
impl_module = importlib.util.module_from_spec(spec)  # module object from the spec
spec.loader.exec_module(impl_module)  # execute the module so attributes are available
CropgroStrawberry = impl_module.CropgroStrawberry  # extract the class definition


def parse_dssat_date(code: str) -> str:  # decode a YYDDD date
    """Convert DSSAT YYDDD date code to YYYY-MM-DD string."""
    year = 2000 + int(code[:2])  # convert first two characters to year
    doy = int(code[2:])  # remaining characters give day of year
    return datetime.strptime(f"{year} {doy}", "%Y %j").strftime("%Y-%m-%d")  # parse and format into ISO date


def parse_srx_file(path: str):  # read planting date and station from experiment
    """Extract planting date and weather station code from an SRX file."""
    planting_code = None  # placeholder for planting date code
    wsta = None  # placeholder for weather station code
    with open(path) as f:  # open the SRX experiment file
        lines = f.readlines()  # read all lines into memory
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
    planting_date = parse_dssat_date(planting_code) if planting_code else None  # convert code to date string if found
    return planting_date, wsta  # return extracted values


def read_wth_file(path: str) -> pd.DataFrame:  # read weather data from .WTH
    """Parse a DSSAT .WTH file into a DataFrame."""
    with open(path) as f:  # open the weather file
        lines = f.readlines()  # read file lines
    start = next(i for i, l in enumerate(lines) if l.startswith("@DATE"))  # locate table header line
    header = lines[start].split()  # obtain column names
    indices = {h: idx for idx, h in enumerate(header)}  # map header names to positions
    records = []  # list to hold daily records
    for line in lines[start + 1 :]:  # process each subsequent line
        if not line.strip() or line.startswith("*"):  # skip blank lines and comments
            continue  # ignore lines that have no data
        parts = line.split()  # split the data fields
        code = parts[0]  # YYDDD code
        date = parse_dssat_date(code)  # convert to ISO date
        rec = {  # build a record for this day
            "date": date,  # date string
            "tmax": float(parts[indices.get("TMAX")]),  # maximum temperature
            "tmin": float(parts[indices.get("TMIN")]),  # minimum temperature
            "solar_radiation": float(parts[indices.get("SRAD")]),  # solar radiation
            "rainfall": float(parts[indices.get("RAIN")]) if "RAIN" in indices else 0.0,  # rainfall amount
            "rh": float(parts[indices.get("RHUM")]) if "RHUM" in indices else 70.0,  # relative humidity
            "wind_speed": float(parts[indices.get("WIND")]) if "WIND" in indices else 2.0,  # wind speed
        }  # end of record dictionary
        records.append(rec)  # store the day's data
    return pd.DataFrame(records)  # convert list to DataFrame


def run_dssat(srx_path: str, dssat_dir: str):  # invoke the DSSAT executable
    """Run DSSAT using Utilities/run_dssat for the provided SRX file."""
    util = os.path.join(dssat_dir, "Utilities", "run_dssat")  # path to run_dssat utility
    if not os.path.exists(util):  # ensure the utility exists
        raise FileNotFoundError(f"run_dssat not found at {util}")  # raise if run_dssat cannot be found
    subprocess.run([util, os.path.basename(srx_path)], cwd=os.path.dirname(srx_path), check=True)  # execute run_dssat in experiment directory


def read_fortran_output(exp_dir: str) -> pd.DataFrame:  # read DSSAT output files
    """Load summary.csv or PlantGro.OUT produced by DSSAT."""
    summary_path = os.path.join(exp_dir, "summary.csv")  # check for CSV summary
    if os.path.exists(summary_path):  # load CSV if present
        return pd.read_csv(summary_path)  # return DataFrame
    pg_path = os.path.join(exp_dir, "PlantGro.OUT")  # fallback to PlantGro.OUT
    if os.path.exists(pg_path):  # load fixed width file
        return pd.read_fwf(pg_path, skiprows=4)  # return DataFrame
    raise FileNotFoundError("No DSSAT output found")  # raise if neither output exists


def run_python_model(wth_df: pd.DataFrame, planting_date: str):  # simulate growth using Python model
    soil = {"max_root_depth": 50.0, "field_capacity": 200.0, "wilting_point": 50.0}  # simple soil parameters
    cultivar = {  # cultivar traits
        "name": "Generic",  # cultivar name
        "tbase": 4.0,  # base temperature
        "topt": 22.0,  # optimum temperature
        "tmax_th": 35.0,  # maximum threshold
        "rue": 2.5,  # radiation use efficiency
        "k_light": 0.6,  # light extinction coefficient
        "sla": 0.02,  # specific leaf area
        "potential_fruits_per_crown": 10.0,  # fruit potential
    }
    model = CropgroStrawberry(40.0, planting_date, soil, cultivar)  # instantiate the model
    return model.simulate_growth(wth_df)  # run the simulation


def main():  # orchestrate the comparison
    parser = argparse.ArgumentParser(description="Compare DSSAT and Python model outputs")  # set up CLI parser
    parser.add_argument("srx", help="Path to DSSAT .SRX file")  # SRX experiment path
    parser.add_argument("--dssat-dir", default="dssat-csm-os-develop", help="DSSAT installation directory")  # directory with DSSAT build
    args = parser.parse_args()  # parse arguments

    planting_date, wsta = parse_srx_file(args.srx)  # extract info from SRX
    if planting_date is None or wsta is None:  # validate required data
        raise ValueError("Could not parse SRX file")  # stop if SRX is malformed

    run_dssat(args.srx, args.dssat_dir)  # generate Fortran output

    exp_dir = os.path.dirname(args.srx)  # directory containing outputs
    fort_df = read_fortran_output(exp_dir)  # load DSSAT results

    year = planting_date[:4]  # extract year for weather search
    weather_dir = os.path.join("dssat-csm-data-develop", "Weather")  # base directory for weather files
    pattern = f"{wsta}{year[2:]}*.WTH"  # expected weather filename pattern
    matches = [f for f in os.listdir(weather_dir) if f.startswith(f"{wsta}{year[2:]}") and f.endswith(".WTH")]  # search for matching file
    if not matches:  # ensure weather file exists
        raise FileNotFoundError("Weather file not found")  # abort if missing
    wth_path = os.path.join(weather_dir, matches[0])  # take first matching weather file
    wth_df = read_wth_file(wth_path)  # load weather into DataFrame

    py_df = run_python_model(wth_df, planting_date)  # run our Python model

    pdt.assert_frame_equal(py_df.head(len(fort_df)), fort_df.head(len(py_df)), check_dtype=False)  # verify outputs match
    print("Python model output matches DSSAT output")  # inform the user


if __name__ == "__main__":  # run when executed directly
    main()  # start the program
