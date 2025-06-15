# CROPGRO-Strawberry Model

This repository contains a Python implementation of the CROPGRO-Strawberry crop model adapted from the DSSAT framework. The model simulates strawberry growth and development in response to daily weather conditions, soil properties and cultivar characteristics.

## Key Inputs

- **Geographic information**
  - Latitude for daylength calculation
  - Planting date
- **Soil properties**
  - Maximum root depth (cm)
  - Field capacity (mm/m)
  - Wilting point (mm/m)
- **Cultivar parameters**
  - Base temperature (°C)
  - Optimal temperature (°C)
  - Maximum threshold temperature (°C)
  - Radiation use efficiency (g/MJ)
  - Light extinction coefficient
  - Specific leaf area (m²/g)
  - Potential fruits per crown
- **Daily weather data**
  - Maximum and minimum temperatures (°C)
  - Solar radiation (MJ/m²)
  - Rainfall (mm)
  - Relative humidity (%)
  - Wind speed (m/s)

## Key Outputs

- **Plant growth metrics**
  - Total plant biomass (g/plant)
  - Organ-specific biomass
  - Leaf area index (m²/m²)
  - Root depth (cm)
- **Reproductive development**
  - Fruit number (fruits/plant)
  - Fruit biomass (g/plant)
  - Crown number (crowns/plant)
  - Runner number (runners/plant)
- **Physiological processes**
  - Phenological stage
  - Accumulated thermal time (degree-days)
  - Daily photosynthesis rate
  - Transpiration rate
  - Water stress factor
- **Time series data**
  - Daily values for all plant state variables
  - Progress through development stages

## Setup

Requirements:

- Python 3
- `numpy`
- `pandas`
- `matplotlib`

Install the dependencies using `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Running the example

Execute the model with the bundled synthetic weather data:

```bash
python cropgro-strawberry-implementation.py
```

The script prints final statistics and displays plots of simulated growth.

## Running the tests

A unit test suite is provided. Run it with:

```bash
python cropgro-strawberry-test1.py
```

## Running the original DSSAT code

The repository also includes the full Fortran source of DSSAT in the `dssat-csm-os-develop` directory. Build it using CMake:

```bash
cd dssat-csm-os-develop
mkdir build
cd build
cmake ..
make
```

After compilation the `run_dssat` helper script is generated in `Utilities`. Invoke it with a Strawberry `.SRX` experiment file:

```bash
./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1601.SRX
```

### Building on macOS

Install `cmake` and `gcc` (providing `gfortran`), for example via Homebrew:

```bash
brew install cmake gcc
```

Run the helper script to compile and install DSSAT. The script also copies the
sample strawberry experiments and weather files, generates a `STRB.V48` batch
file, and executes the model, writing results to `/usr/local/BatchFiles`:

```bash
./scripts/build_dssat_macos.sh
```

### Building on Windows

Install CMake and a gfortran toolchain such as MinGW-w64. The Windows batch file
performs the same actions as the macOS script: build, install, stage the
strawberry data and run the simulation. Execute it from a Windows terminal:

```cmd
scripts\build_dssat_windows.cmd
```

`build_dssat_windows.cmd` is a Windows batch file that relies on the `cmd.exe`
shell and Windows-specific commands such as `xcopy` and `mingw32-make`. A macOS
terminal doesn’t provide these commands or the Windows environment expected by
the script. Instead, macOS users should run the companion script
`scripts/build_dssat_macos.sh`, which performs the same setup using standard
Unix tools. To run the Windows batch file on macOS you’d need a Windows
environment (e.g., a VM or Wine).

## Comparing with the Fortran DSSAT model

To verify the Python implementation against the official Fortran code, use `validate_models.py`. The script requires a compiled DSSAT installation containing `Utilities/run_dssat`.

```bash

python compare_with_fortran.py dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir dssat-csm-os-develop

python validate_models.py ./dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir dssat-csm-os-develop --tolerance 1.0
```



## Automated validation

Use `validate_models.py` to automatically run the official DSSAT executable and the Python implementation, then compare their outputs. The script writes a simple report listing the maximum difference for each common column and whether the results are within the specified tolerance.

```bash
python validate_models.py ./dssat-csm-data-develop/Strawberry/UFBA1601.SRX --dssat-dir dssat-csm-os-develop --tolerance 1.0
```

See [docs/student_guide.md](docs/student_guide.md) for a concise, step-by-step guide to running the Python model and comparing it with the official DSSAT code.

### Full comparison pipeline

Run `scripts/run_full_comparison.py` to build DSSAT (if needed) and validate all sample experiments. The script detects your operating system and invokes the appropriate build helper automatically. Reports are saved in `comparison_reports/`.

```bash
python scripts/run_full_comparison.py
```


After running the pipeline you can visualize the validation summaries with `scripts/plot_results.py`:

```bash
python scripts/plot_results.py --reports comparison_reports
```


