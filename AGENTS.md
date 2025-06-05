# Developer Guide

This repository contains a Python implementation of the DSSAT strawberry model along with scripts to build and compare the official Fortran version. Use this guide to keep contributions consistent.

## Environment

- Python 3.8+.
- Install requirements with `pip install -r requirements.txt`.
- Fortran code can be built using scripts in `scripts/`.

## Running the Python model

```bash
python cropgro-strawberry-implementation.py
```

Use the bundled synthetic weather data or adjust the script for your dataset.

## Building and running DSSAT

- **macOS**: `bash scripts/build_dssat_macos.sh`
- **Windows**: `scripts\build_dssat_windows.cmd`
- Run a compiled DSSAT executable using `python run_original_dssat.py path/to/experiment.SRX`.

## Comparing outputs

- `python compare_with_fortran.py path/to/experiment.SRX` checks the Python results against the Fortran model.
- `python validate_models.py path/to/experiment.SRX --tolerance 1.0` generates a small report of differences.

## Tests

Run the unit tests before committing:

```bash
python cropgro-strawberry-test1.py
```

## Commit messages

Use concise, imperative descriptions (e.g. "Add validation script" or "Fix growth rate calculation"). If a change touches the model logic, note any effects on the outputs.

## Documentation

Additional details are found in `docs/student_guide.md` and the project `README.md`.

