"""Helper script to execute the original DSSAT strawberry model."""

import argparse
import os
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Execute the original DSSAT strawberry model on macOS"
    )
    parser.add_argument(
        "experiment",
        help="Path to a DSSAT .SRX experiment file"
    )
    parser.add_argument(
        "--dssat-dir",
        default="dssat-csm-os-develop",
        help=(
            "Directory containing the DSSAT build or installation. "
            "Must include Utilities/run_dssat"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="dssat_results",
        help="Directory where output files will be copied",
    )
    args = parser.parse_args()

    exp_path = Path(args.experiment).resolve()
    dssat_dir = Path(args.dssat_dir).resolve()
    out_dir = Path(args.output_dir).resolve()

    util = dssat_dir / "Utilities" / "run_dssat"
    if not util.exists():
        raise FileNotFoundError(f"run_dssat not found at {util}")

    # Execute DSSAT in the experiment's directory
    subprocess.run([str(util), exp_path.name], cwd=exp_path.parent, check=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ["summary.csv", "PlantGro.OUT"]:
        src = exp_path.parent / name
        if src.exists():
            shutil.copy2(src, out_dir / src.name)


if __name__ == "__main__":
    main()
