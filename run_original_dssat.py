"""Helper script to execute the original DSSAT strawberry model."""

import argparse  # command line parsing utilities
import os  # operating system interfaces
import shutil  # high level file operations for copying
import subprocess  # run external programs
from pathlib import Path  # filesystem path objects


def main():  # main entry point for the script
    parser = argparse.ArgumentParser(
        description="Execute the original DSSAT strawberry model on macOS"  # shown in help text
    )
    parser.add_argument(
        "experiment",  # required path to a DSSAT experiment file
        help="Path to a DSSAT .SRX experiment file",
    )
    parser.add_argument(
        "--dssat-dir",  # directory containing the DSSAT installation
        default="dssat-csm-os-develop",
        help=(
            "Directory containing the DSSAT build or installation. "
            "Must include Utilities/run_dssat"  # ensure the run_dssat helper exists
        ),
    )
    parser.add_argument(
        "--output-dir",  # optional directory for results
        default="dssat_results",
        help="Directory where output files will be copied",
    )
    args = parser.parse_args()  # parse command line options

    exp_path = Path(args.experiment).resolve()  # absolute path to experiment
    dssat_dir = Path(args.dssat_dir).resolve()  # absolute path to DSSAT install
    out_dir = Path(args.output_dir).resolve()  # absolute path for outputs

    util = dssat_dir / "Utilities" / "run_dssat"  # path to the DSSAT runner
    if not util.exists():  # verify run_dssat is available
        raise FileNotFoundError(f"run_dssat not found at {util}")

    # execute DSSAT from within the experiment directory
    subprocess.run([str(util), exp_path.name], cwd=exp_path.parent, check=True)

    out_dir.mkdir(parents=True, exist_ok=True)  # create output directory if needed
    for name in ["summary.csv", "PlantGro.OUT"]:  # known output files to copy
        src = exp_path.parent / name
        if src.exists():
            shutil.copy2(src, out_dir / src.name)  # preserve metadata when copying


if __name__ == "__main__":  # run only when executed directly
    main()
