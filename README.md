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

=======

## Comparing with the Fortran DSSAT model

To verify the Python implementation against the official Fortran code, use `compare_with_fortran.py`. The script requires a compiled DSSAT installation containing `Utilities/run_dssat`.

```bash
python compare_with_fortran.py path/to/UFBA1401.SRX --dssat-dir dssat-csm-os-develop
```


