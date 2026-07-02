#!/usr/bin/env python3
"""Reproduce the UFBA1401 DSSAT-vs-Python comparison data and plot."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

KG_HA_PER_G_PLANT = 43.0
FRUIT_NUMBER_TO_GAD = 795.5

VARIABLES = [
    ("LAID", "leaf_area_index", "Leaf Area Index (LAID)", "Leaf Area Index (LAID) [m2/m2]"),
    ("LWAD", "leaf_biomass", "Leaf Biomass (LWAD)", "Leaf Biomass (LWAD) [kg/ha]"),
    ("SWAD", "stem_biomass", "Stem Biomass (SWAD)", "Stem Biomass (SWAD) [kg/ha]"),
    ("GWAD", "seed_biomass", "Fruit Biomass (GWAD)", "Fruit Biomass (GWAD) [kg/ha]"),
    ("RWAD", "root_biomass", "Root Biomass (RWAD)", "Root Biomass (RWAD) [kg/ha]"),
    ("VWAD", "vwad", "Total Biomass (VWAD)", "Total Biomass (VWAD) [kg/ha]"),
    ("G#AD", "fruit_number", "Fruit Number (G#AD)", "Fruit Number (G#AD) [no./m2]"),
    ("RDPD", "root_depth", "Root Depth (RDPD)", "Root Depth (RDPD) [m]"),
]


def import_model(repo_dir: Path):
    model_path = repo_dir / "cropgro-strawberry-implementation.py"
    spec = importlib.util.spec_from_file_location("cropgro_strawberry_implementation", model_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import model from {model_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_plantgro(path: Path, experiment: str) -> pd.DataFrame:
    lines = path.read_text(errors="ignore").splitlines()
    current_experiment = ""
    selected_header = None
    rows: list[dict[str, str]] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("EXPERIMENT"):
            current_experiment = stripped
            continue

        if line.startswith("@YEAR"):
            header = line.replace("@", "").split()
            if experiment in current_experiment:
                selected_header = header
                rows = []
            else:
                selected_header = None
            continue

        if selected_header is None:
            continue

        parts = line.split()
        if not parts or not parts[0].isdigit():
            if rows:
                break
            continue
        if len(parts) >= len(selected_header):
            rows.append(dict(zip(selected_header, parts)))

    if not rows:
        raise ValueError(f"No PlantGro rows found for {experiment} in {path}")

    df = pd.DataFrame(rows)
    for column in df.columns:
        converted = pd.to_numeric(df[column], errors="coerce")
        df[column] = converted if not converted.isna().all() else df[column]
    return df


def run_python_model(repo_dir: Path, weather_paths: list[Path], n_days: int) -> pd.DataFrame:
    module = import_model(repo_dir)

    from load_dssat_weather import load_dssat_weather

    weather_df = load_dssat_weather(
        [str(path) for path in weather_paths],
        planting_dssat_date=14282,
        n_days=n_days,
    )
    soil_properties = {
        "max_root_depth": 200.0,
        "field_capacity": 200.0,
        "wilting_point": 50.0,
    }
    cultivar_params = {
        "name": "Radiance",
        "kcan": 0.67,
        "kc_slope": 0.50,
        "rowspc": 1.21,
        "pltpop": 4.3,
        "sla": 0.0165,
    }
    model = module.CropgroStrawberry(
        latitude=27.76,
        planting_date="2014-10-09",
        soil_properties=soil_properties,
        cultivar_params=cultivar_params,
    )
    return model.simulate_growth(weather_df)


def convert_python_output(py_df: pd.DataFrame, length: int) -> pd.DataFrame:
    data = {
        "DAP": py_df["dap"].iloc[:length].to_numpy(),
        "LAID": py_df["leaf_area_index"].iloc[:length].to_numpy(),
        "LWAD": py_df["leaf_biomass"].iloc[:length].to_numpy() * KG_HA_PER_G_PLANT,
        "SWAD": py_df["stem_biomass"].iloc[:length].to_numpy() * KG_HA_PER_G_PLANT,
        "GWAD": py_df["seed_biomass"].iloc[:length].to_numpy() * KG_HA_PER_G_PLANT,
        "RWAD": py_df["root_biomass"].iloc[:length].to_numpy() * KG_HA_PER_G_PLANT,
        "VWAD": (
            py_df["leaf_biomass"].iloc[:length].to_numpy()
            + py_df["stem_biomass"].iloc[:length].to_numpy()
        )
        * KG_HA_PER_G_PLANT,
        "G#AD": py_df["fruit_number"].iloc[:length].to_numpy() * FRUIT_NUMBER_TO_GAD,
        "RDPD": py_df["root_depth"].iloc[:length].to_numpy() / 100.0,
    }
    return pd.DataFrame(data)


def build_comparison(dssat_df: pd.DataFrame, python_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(python_df) < len(dssat_df):
        raise ValueError(
            f"Python output has {len(python_df)} rows, fewer than DSSAT output {len(dssat_df)} rows"
        )

    length = len(dssat_df)
    python_converted = convert_python_output(python_df, length)
    dssat_dap = dssat_df["DAP"].iloc[:length].reset_index(drop=True)
    python_dap = python_converted["DAP"].reset_index(drop=True)
    if not dssat_dap.equals(python_dap):
        raise ValueError("DSSAT and Python outputs are not aligned by DAP")

    detailed = pd.DataFrame({"DAP": dssat_df["DAP"].iloc[:length].to_numpy()})
    summary_rows = []

    for dssat_col, _, _, _ in VARIABLES:
        dssat_values = pd.to_numeric(dssat_df[dssat_col].iloc[:length], errors="coerce")
        python_values = python_converted[dssat_col]
        detailed[f"{dssat_col}_DSSAT"] = dssat_values.to_numpy()
        detailed[f"{dssat_col}_Python"] = python_values.to_numpy()
        detailed[f"{dssat_col}_Diff"] = dssat_values.to_numpy() - python_values.to_numpy()

        summary_rows.append(
            {
                "Variable": dssat_col,
                "DSSAT_Mean": dssat_values.mean(),
                "Python_Mean": python_values.mean(),
                "Correlation": dssat_values.corr(python_values),
                "DSSAT_Max": dssat_values.max(),
                "Python_Max": python_values.max(),
                "DSSAT_Min": dssat_values.min(),
                "Python_Min": python_values.min(),
            }
        )

    return detailed, pd.DataFrame(summary_rows)


def plot_comparison(detailed: pd.DataFrame, summary: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    axes = axes.ravel()

    for index, (dssat_col, _, title, ylabel) in enumerate(VARIABLES):
        ax = axes[index]
        dssat_values = detailed[f"{dssat_col}_DSSAT"]
        python_values = detailed[f"{dssat_col}_Python"]
        correlation = summary.loc[summary["Variable"] == dssat_col, "Correlation"].iloc[0]

        ax.plot(detailed["DAP"], dssat_values, marker="o", markersize=2.5, linewidth=1.4, label="DSSAT (Docker)")
        ax.plot(detailed["DAP"], python_values, marker="s", markersize=2.5, linewidth=1.4, label="Python")
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlabel("Days After Planting (DAP)", fontsize=9)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8, loc="best")
        ax.text(
            0.02,
            0.95,
            f"r = {correlation:.3f}",
            transform=ax.transAxes,
            va="top",
            fontsize=8,
            bbox={"facecolor": "#f4e6c1", "edgecolor": "#a78b5a", "boxstyle": "round,pad=0.2"},
        )

    ax = axes[-1]
    labels = summary["Variable"].tolist()
    x_positions = range(len(labels))
    width = 0.38
    ax.bar([x - width / 2 for x in x_positions], summary["DSSAT_Mean"], width=width, label="DSSAT (Docker)")
    ax.bar([x + width / 2 for x in x_positions], summary["Python_Mean"], width=width, label="Python")
    ax.set_title("Mean Value Comparison", fontsize=11, fontweight="bold")
    ax.set_xlabel("Variable", fontsize=9)
    ax.set_ylabel("Mean Value", fontsize=9)
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8, loc="best")

    fig.suptitle(
        "DSSAT (Docker/Fortran) vs Python Strawberry Model Comparison\n"
        "Experiment: UFBA1401 | Planting Date: 2014-10-09\n"
        "(Real outputs from both models, unit-converted for comparison)",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dssat-output", default="dssat_results/UFBA1401/PlantGro.OUT")
    parser.add_argument("--output-dir", default="comparison_results")
    parser.add_argument("--n-days", type=int, default=110)
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent
    dssat_path = repo_dir / args.dssat_output
    output_dir = repo_dir / args.output_dir
    weather_paths = [
        repo_dir / "weather" / "UFBA1401.WTH",
        repo_dir / "weather" / "UFBA1501.WTH",
    ]

    dssat_df = parse_plantgro(dssat_path, experiment="UFBA1401")
    python_df = run_python_model(repo_dir, weather_paths, args.n_days)
    detailed, summary = build_comparison(dssat_df, python_df)

    output_dir.mkdir(parents=True, exist_ok=True)
    detailed.to_csv(output_dir / "dssat_python_detailed_comparison.csv", index=False)
    summary.to_csv(output_dir / "dssat_python_summary_comparison.csv", index=False)
    plot_comparison(detailed, summary, output_dir / "ufba1401_dssat_python_comparison.png")

    print(summary[["Variable", "DSSAT_Mean", "Python_Mean", "Correlation"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
