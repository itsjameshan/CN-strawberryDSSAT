"""Utility functions to compare DSSAT Fortran output with the Python model."""

import argparse
import os
import pandas as pd


def read_fortran_output(path: str) -> pd.DataFrame:
    """Load DSSAT output from summary.csv or PlantGro.OUT."""
    if os.path.isdir(path):
        csv_path = os.path.join(path, "summary.csv")
        if os.path.exists(csv_path):
            return pd.read_csv(csv_path)
        pg_path = os.path.join(path, "PlantGro.OUT")
        if os.path.exists(pg_path):
            return pd.read_fwf(pg_path, skiprows=4)
        raise FileNotFoundError("No DSSAT output found in directory")
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_fwf(path, skiprows=4)


def read_python_output(path: str) -> pd.DataFrame:
    """Load CSV produced by the Python model."""
    return pd.read_csv(path)


def extract_yield(df: pd.DataFrame):
    """Return final yield value from DataFrame if possible."""
    yield_cols = [
        "fruit_biomass",
        "YIELD",
        "TOTYLD",
        "HWAM",
        "CWAM",
        "harvest_yield",
    ]
    for col in yield_cols:
        if col in df.columns:
            return float(df[col].iloc[-1])
    return None


def extract_stages(df: pd.DataFrame):
    """Return a mapping of stage name to first day after planting."""
    if "stage" not in df.columns:
        return {}
    if "dap" in df.columns:
        day_col = "dap"
    elif "DAP" in df.columns:
        day_col = "DAP"
    elif "das" in df.columns:
        day_col = "das"
    else:
        return {}
    stages = {}
    for stage in df["stage"].unique():
        idx = df[df["stage"] == stage].index[0]
        stages[stage] = int(df.loc[idx, day_col])
    return stages


def compare_metrics(fort_df: pd.DataFrame, py_df: pd.DataFrame) -> str:
    """Generate summary of differences between two outputs."""
    report_lines = []
    f_yield = extract_yield(fort_df)
    p_yield = extract_yield(py_df)
    if f_yield is not None and p_yield is not None:
        diff = p_yield - f_yield
        report_lines.append(
            f"Yield difference: Python={p_yield:.2f}, Fortran={f_yield:.2f}, diff={diff:.2f}"
        )
    elif f_yield is not None or p_yield is not None:
        report_lines.append("Yield data missing in one of the outputs")

    f_stages = extract_stages(fort_df)
    p_stages = extract_stages(py_df)
    common_stages = set(f_stages) & set(p_stages)
    for stage in sorted(common_stages):
        diff = p_stages[stage] - f_stages[stage]
        report_lines.append(
            f"Stage {stage}: Python DAP={p_stages[stage]}, Fortran DAP={f_stages[stage]}, diff={diff}"
        )
    missing = set(f_stages) ^ set(p_stages)
    for stage in sorted(missing):
        src = "Python" if stage in p_stages else "Fortran"
        report_lines.append(f"Stage {stage} only present in {src} output")

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="Compare DSSAT and Python outputs")
    parser.add_argument("fortran_output", help="Path to summary.csv or PlantGro.OUT from DSSAT")
    parser.add_argument("python_output", help="CSV file produced by Python model")
    args = parser.parse_args()

    fort_df = read_fortran_output(args.fortran_output)
    py_df = read_python_output(args.python_output)

    summary = compare_metrics(fort_df, py_df)
    print("Summary report:\n" + summary)


if __name__ == "__main__":
    main()
