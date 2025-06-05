"""Run the full DSSAT comparison pipeline.

`build_dssat_windows.cmd` is a Windows batch file that relies on the
`cmd.exe` shell and Windows-specific commands such as `xcopy` and
`mingw32-make`. A macOS terminal doesn’t provide these commands or the
Windows environment expected by the script. Instead, macOS users should run
the companion script `scripts/build_dssat_macos.sh`, which performs the same
setup using standard Unix tools. To run the Windows batch file on macOS you’d
need a Windows environment (e.g., a VM or Wine).
"""

import os
import subprocess
import sys
import glob
from pathlib import Path
import platform


def build_dssat(dssat_dir: str) -> None:
    """Build DSSAT if ``Utilities/run_dssat`` is missing.

    The build method is chosen based on the current operating system. macOS
    invokes ``build_dssat_macos.sh`` while Windows uses ``build_dssat_windows.cmd``.
    Other platforms fall back to a direct ``cmake``/``make`` build.
    """
    util = Path(dssat_dir) / "Utilities" / "run_dssat"
    if util.exists():
        print("DSSAT already built")
        return
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["bash", "scripts/build_dssat_macos.sh"], check=True)
        return
    if system == "Windows":
        subprocess.run(["cmd", "/c", "scripts\\build_dssat_windows.cmd"], check=True)
        return
    build_dir = Path(dssat_dir) / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cmake", ".."], cwd=build_dir, check=True)
    subprocess.run(["make"], cwd=build_dir, check=True)


def run_validation(srx: str, dssat_dir: str, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / (Path(srx).stem + ".txt")
    subprocess.run(
        [sys.executable, "validate_models.py", srx, "--dssat-dir", dssat_dir, "--report", str(report_path)],
        check=True,
    )


def main() -> None:
    dssat_dir = "dssat-csm-os-develop"
    build_dssat(dssat_dir)
    report_dir = Path("comparison_reports")
    experiments = sorted(glob.glob("dssat-csm-data-develop/Strawberry/*.SRX"))
    if not experiments:
        print("No SRX experiments found")
        return
    for srx in experiments:
        print(f"Validating {srx}...")
        run_validation(srx, dssat_dir, report_dir)
    print(f"Reports written to {report_dir}")


if __name__ == "__main__":
    main()
