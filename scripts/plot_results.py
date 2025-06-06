"""Plot validation summaries produced by DSSAT comparison scripts."""

import argparse
import glob
import os
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_validation_report(path: str) -> dict:
    """Return dictionary of metrics extracted from a validation report."""
    metrics = {}
    with open(path) as f:
        lines = f.readlines()
    if lines:
        metrics["status"] = "PASSED" if "PASSED" in lines[0] else "FAILED"
    for line in lines[1:]:
        m = re.search(r"^(.*): max abs diff ([0-9.eE+-]+)", line.strip())
        if m:
            metrics[m.group(1).strip()] = float(m.group(2))
    return metrics


def gather_reports(directory: str) -> pd.DataFrame:
    """Load all validation reports in a directory into a DataFrame."""
    records = {}
    for path in sorted(glob.glob(os.path.join(directory, "*.txt"))):
        name = Path(path).stem
        records[name] = parse_validation_report(path)
    df = pd.DataFrame(records).T
    return df


def plot_report_dataframe(df: pd.DataFrame) -> plt.Figure:
    """Plot a bar chart of maximum absolute differences."""
    metric_cols = [c for c in df.columns if c != "status"]
    if not metric_cols:
        raise ValueError("No numeric metrics found in reports")
    ax = df[metric_cols].plot(kind="bar", figsize=(10, 6))
    ax.set_ylabel("Max Absolute Difference")
    ax.set_xlabel("Experiment")
    ax.set_title("Model Validation Results")
    plt.tight_layout()
    return ax.get_figure()


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot validation results")
    parser.add_argument(
        "--reports",
        default="comparison_reports",
        help="Directory containing validation report text files",
    )
    parser.add_argument(
        "--save",
        help="Path to save the plot. If omitted the plot is shown interactively",
    )
    args = parser.parse_args()

    df = gather_reports(args.reports)
    if df.empty:
        print("No reports found")
        return
    fig = plot_report_dataframe(df)
    if args.save:
        fig.savefig(args.save)
    else:
        plt.show()


if __name__ == "__main__":
    main()
