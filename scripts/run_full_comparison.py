"""Run the full DSSAT comparison pipeline.

This script builds the official Fortran DSSAT model and then executes the
``validate_models.py`` helper over every ``.SRX`` experiment in the data
directory.  The validation script compares the Fortran results against the
Python implementation and writes a text report for each experiment.

The notes below explain why we provide separate build scripts for macOS and
Windows users.

``build_dssat_windows.cmd`` is a Windows batch file that relies on the
``cmd.exe`` shell and Windows specific tools such as ``xcopy`` and
``mingw32-make``.  These commands are not available in a standard macOS
terminal.  macOS users should therefore run the companion shell script
``scripts/build_dssat_macos.sh`` which performs the same setup using Unix
tools.  Running the Windows batch file on macOS would require a full Windows
environment (for example a VM or Wine).
"""

import os
import subprocess
import sys
import glob
from pathlib import Path
import platform


def build_dssat(dssat_dir: str) -> None:
    """Compile the Fortran DSSAT model if it has not been built yet.

    The function checks for the presence of the ``run_dssat`` utility in the
    ``Utilities`` folder.  If it is missing, the model is built using platform
    specific scripts on macOS or Windows.  All other platforms perform a
    standard ``cmake``/``make`` build.
    """

    util = Path(dssat_dir) / "Utilities" / "run_dssat"          # expected executable path
    if util.exists():                                           # skip build when executable exists
        print("DSSAT already built")                            # notify the user
        return                                                  # nothing else to do
    system = platform.system()                                  # determine the host operating system
    if system == "Darwin":                                      # macOS build path
        subprocess.run(["bash", "scripts/build_dssat_macos.sh"], check=True)  # call shell script
        return                                                  # exit after successful build
    if system == "Windows":                                     # Windows build path
        subprocess.run(["cmd", "/c", "scripts\\build_dssat_windows.cmd"], check=True)  # call batch file
        return                                                  # exit after successful build
    build_dir = Path(dssat_dir) / "build"                       # generic build directory
    build_dir.mkdir(parents=True, exist_ok=True)                # ensure the directory exists
    subprocess.run(["cmake", ".."], cwd=build_dir, check=True)  # configure the project
    subprocess.run(["make"], cwd=build_dir, check=True)         # compile using make


def run_validation(srx: str, dssat_dir: str, report_dir: Path) -> None:
    """Validate a single SRX experiment against the Python model."""

    report_dir.mkdir(parents=True, exist_ok=True)                 # create directory for reports
    report_path = report_dir / (Path(srx).stem + ".txt")           # determine output file for this experiment
    subprocess.run(                                                # invoke the comparison helper
        [sys.executable, "validate_models.py", srx,                #   python executable and script name
         "--dssat-dir", dssat_dir, "--report", str(report_path)],  #   pass DSSAT directory and report path
        check=True,                                                #   raise an error if the command fails
    )


def main() -> None:
    """Entry point for the comparison workflow."""

    dssat_dir = "dssat-csm-os-develop"                           # location of the DSSAT source tree
    build_dssat(dssat_dir)                                        # ensure the Fortran model is built
    report_dir = Path("comparison_reports")                       # directory to store validation outputs
    experiments = sorted(glob.glob("dssat-csm-data-develop/Strawberry/*.SRX"))  # list of experiment files
    if not experiments:                                           # if no experiments were found
        print("No SRX experiments found")                          #   inform the user
        return                                                    #   abort the run
    for srx in experiments:                                       # iterate over each experiment
        print(f"Validating {srx}...")                              #   show which file is being processed
        run_validation(srx, dssat_dir, report_dir)                 #   run the validation step
    print(f"Reports written to {report_dir}")                      # summary message when done


if __name__ == "__main__":
    main()                                                     # run the workflow when executed directly
