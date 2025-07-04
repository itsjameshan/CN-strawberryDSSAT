"""Plot validation summaries produced by DSSAT comparison scripts."""

import argparse
import glob
import os
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_validation_report(path: str) -> dict:
    """Read a validation report and return extracted metrics.

    The report is expected to contain a status line followed by metric
    lines formatted as ``"<name>: max abs diff <value>"``.
    """
    metrics = {}  # container for parsed metrics
    with open(path) as f:  # open the report file
        lines = f.readlines()  # read all lines from the file
    if lines:  # only process if the file was not empty
        # determine whether the validation passed or failed
        metrics["status"] = "PASSED" if "PASSED" in lines[0] else "FAILED"
    for line in lines[1:]:  # iterate over each metric line
        # look for the metric pattern "name: max abs diff value"
        m = re.search(r"^(.*): max abs diff ([0-9.eE+-]+)", line.strip())
        if m:  # if a metric was found on this line
            # store the metric name and floating point value
            metrics[m.group(1).strip()] = float(m.group(2))
    return metrics  # return the dictionary of metrics


def gather_reports(directory: str) -> pd.DataFrame:
    """Collect metrics from all reports in *directory*.

    Each ``.txt`` file is parsed and the results are assembled into a
    :class:`pandas.DataFrame` where the index represents the experiment
    name (derived from the file name).
    """
    records = {}  # mapping of experiment name to metric dict
    for path in sorted(glob.glob(os.path.join(directory, "*.txt"))):  # iterate through report files
        name = Path(path).stem  # experiment name without extension
        records[name] = parse_validation_report(path)  # parse the file and store metrics
    df = pd.DataFrame(records).T  # create DataFrame with experiments as rows
    return df  # return assembled DataFrame


def plot_report_dataframe(df: pd.DataFrame) -> plt.Figure:
    """Create a bar plot summarizing validation metrics.

    Only numeric columns other than ``"status"`` are plotted.
    """
    metric_cols = [c for c in df.columns if c != "status"]  # select metric columns
    if not metric_cols:  # ensure there is something to plot
        raise ValueError("No numeric metrics found in reports")
    ax = df[metric_cols].plot(kind="bar", figsize=(10, 6))  # draw the bar chart
    ax.set_ylabel("Max Absolute Difference")  # label the y-axis
    ax.set_xlabel("Experiment")  # label the x-axis
    ax.set_title("Model Validation Results")  # set the plot title
    plt.tight_layout()  # adjust layout for better spacing
    return ax.get_figure()  # return the figure object for saving or showing


def main() -> None:
    """Parse arguments, load reports and produce the plot."""
    parser = argparse.ArgumentParser(description="Plot validation results")  # configure CLI parser
    parser.add_argument(  # option for directory containing reports
        "--reports",
        default="comparison_reports",
        help="Directory containing validation report text files",
    )
    parser.add_argument(  # optional path to save the plot
        "--save",
        help="Path to save the plot. If omitted the plot is shown interactively",
    )
    args = parser.parse_args()  # parse command line arguments

    df = gather_reports(args.reports)  # read all report files
    if df.empty:  # if no data was found
        print("No reports found")  # inform the user
        return  # exit early
    fig = plot_report_dataframe(df)  # create the figure
    if args.save:  # decide whether to save or display
        fig.savefig(args.save)  # save to the provided path
    else:
        plt.show()  # show interactively


if __name__ == "__main__":
    main()
