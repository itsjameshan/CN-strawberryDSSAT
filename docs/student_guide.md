# Student Guide: CROPGRO-Strawberry Model

This guide walks you through running the Python implementation of the DSSAT strawberry model, interpreting its output, and comparing it with the official Fortran version.

## 1. Install dependencies

Use `requirements.txt` to install the packages required by the Python scripts:

```bash
pip install -r requirements.txt
```

## 2. Run the Python model

Execute the example script:

```bash
python cropgro-strawberry-implementation.py
```

During execution the model prints intermediate progress. At the end you will see statistics such as:

```
Final biomass: ... g/plant
Final fruit biomass: ... g/plant
Final leaf area index: ... m²/m²
Final phenological stage: ...
```

Plots showing biomass and leaf area development also appear.

## 3. Build and run the official DSSAT code

The repository includes the DSSAT source in `dssat-csm-os-develop`. Build it with CMake:

```bash
cd dssat-csm-os-develop
mkdir build
cd build
cmake ..
make
```

Run an experiment using the bundled data:

```bash
./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1601.SRX
```

## 4. Compare Python output with DSSAT

Two utilities are provided to check the Python results against those from DSSAT.

1. **Direct comparison**:

   ```bash
   python compare_with_fortran.py path/to/UFBA1401.SRX --dssat-dir dssat-csm-os-develop
   ```

   This launches DSSAT for the specified experiment and reports the difference for each variable.

2. **Automated validation**:

   ```bash
   python validate_models.py path/to/UFBA1601.SRX --dssat-dir dssat-csm-os-develop --tolerance 1.0
   ```

   A small report is created listing the maximum difference for each column and whether the results fall within the tolerance threshold.

With these steps you can run the model, analyze its output, and verify that the Python results match the official DSSAT implementation.
