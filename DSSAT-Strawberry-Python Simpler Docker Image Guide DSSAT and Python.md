# DSSAT-Strawberry-Python Docker Image Guide

## Build Image First

```bash
docker build . -f dssat-docker-master/Dockerfile.minimal-python -t dssat-strawberry-python-numba2
```

## Overview

This guide documents the dssat-strawberry-python-numba2 Docker image that combines DSSAT (Decision Support System for Agrotechnology Transfer) with Python environment for running strawberry crop simulations and analysis.

## Image Information

- **Image Name:** dssat-strawberry-python-numba2
- **Image ID:** 0efbd830c067
- **Tag:** latest

## Involved Scripts and Files

### 1. Docker Configuration Files

**dssat-docker-master/Dockerfile.minimal-python** - Main Dockerfile
- Multi-stage build combining DSSAT + Python
- Stage 1: Builds DSSAT from Fortran source code
- Stage 2: Creates Python environment with minimal packages
- Sets up environment paths for both DSSAT and Python

**dssat-docker-master/local.Dockerfile** - Original DSSAT-only reference
- Base Dockerfile for DSSAT compilation only
- Used as reference for the extended version

### 2. Python Dependencies

**requirements.txt** - Minimal Python packages
```
numpy>=1.19.0
pandas>=1.3.0
matplotlib>=3.3.0
numba
```

### 3. Python Scripts (8 files included in image)

1. **cropgro-strawberry-implementation.py** - Main CROPGRO-Strawberry model implementation in Python
2. **cropgro-strawberry-test1.py** - Test script for the strawberry model
3. **compare_with_fortran.py** - Comparison tool between Python and Fortran versions
4. **run_original_dssat.py** - Helper script to run original DSSAT strawberry model
5. **validate_models.py** - Validation script to compare Python model against DSSAT
6. **run_all_comparisons.py** - Batch comparison runner for multiple scenarios
7. **explain_row_differences.py** - Analysis tool for examining result differences
8. **show_dataframe_details.py** - Data analysis utilities for output examination

### 4. DSSAT Source Code

**dssat-docker-master/src/** directory contains:
- Complete DSSAT Fortran source code
- CMakeLists.txt for compilation
- Plant models (Plant/ directory)
- Soil models (Soil/ directory)
- Weather modules (Weather/ directory)
- Input/Output modules
- Utilities and helper functions

## Step-by-Step Usage Guide

### 1. Basic Image Information

```bash
# Check image exists
docker images | grep dssat-strawberry-python-numba2

# Inspect image details
docker inspect dssat-strawberry-python-numba2:latest
```

### 2. Running the Docker Container

#### Interactive Mode (Recommended for testing)

```bash
# Start interactive container with current directory mounted
docker run --rm -it -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest

# Inside container, you'll have access to:
# - /app/dssat/dscsm048 (DSSAT executable)
# - /app/*.py (Python scripts)
# - Python environment with numpy, pandas, matplotlib
```

#### Non-Interactive Mode

```bash
# Run specific commands directly
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python:latest [COMMAND]
```

### 3. Running DSSAT Strawberry Experiments

#### Navigate to Strawberry Data Directory First

```bash
# Ensure you're in the strawberry experiments directory
cd dssat-csm-data-develop/Strawberry

# Verify files exist
ls -la UFBA1401.SRX
```

#### Run Individual Strawberry Experiments

```bash
# Balm 2014 experiment
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1401.SRX
docker run --rm -v ${PWD}:/data -w /data/dssat-csm-data-develop/Strawberry dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1401.SRX

# Balm 2016 experiment
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1601.SRX
docker run --rm -v ${PWD}:/data -w /data/dssat-csm-data-develop/Strawberry dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1601.SRX

# Balm 2017 experiment
docker run --rm -v ${PWD}:/data -w /data/dssat-csm-data-develop/Strawberry dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1701.SRX
```

#### Expected DSSAT Output

```
RUN    TRT FLO MAT TOPWT HARWT  RAIN  TIRR   CET  PESW  TNUP  TNLF TSON TSOC
           dap dap kg/ha kg/ha    mm    mm    mm    mm kg/ha kg/ha kg/ha t/ha
  1 SR   1  23 -99  1804    52   -99     0   -99   -99     0   -99    0   26
```

#### Run Batch Strawberry Experiments

```bash
# First create batch file (if not exists)
cd ../  # Go to dssat-csm-data-develop directory

# Create Docker-compatible batch file using the working version
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest bash -c "sed 's|C:\\\\DSSAT48\\\\Strawberry\\\\|/data/Strawberry/|g' /app/dssat/BatchFiles/Strawberry.v48 > /data/dssat-csm-data-develop/StrawberryDockerCreate1.v48"

# Run batch experiments
# Must cd to local CN-strawberryDSSAT-main/dssat-csm-data-develop first
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 B StrawberryDocker_duan.v48
```

### Path Mapping Explanation

Let me explain the path mapping when you're in the `dssat-csm-data-develop/` directory:

#### Your Current Location
```
/mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main/dssat-csm-data-develop/
```

#### When you run: `-v ${PWD}:/data`

**What happens:**
- **`${PWD}`** = `/mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main/dssat-csm-data-develop/`
- **Docker mounts:** This entire directory to `/data` inside the container

**So the mapping is:**
```
Host: /mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main/dssat-csm-data-develop/
  ↓
Container: /data/
```

**Therefore:**
- **`/data/StrawberryDockerCreate1.v48`** (inside container)
- **Points to:** `/mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main/dssat-csm-data-develop/StrawberryDockerCreate1.v48` (on host)

#### Visual Example

**Host file system:**
```
CN-strawberryDSSAT-main/
├── dssat-csm-data-develop/          ← You are here (${PWD})
│   ├── StrawberryDocker_duan.v48
│   └── StrawberryDockerCreate1.v48  ← File will be created here
└── other-folders/
```

**Container file system:**
```
/data/                               ← Mounted from ${PWD}
├── StrawberryDocker_duan.v48
└── StrawberryDockerCreate1.v48      ← This is /data/StrawberryDockerCreate1.v48
```

#### Key Point
Docker always mounts **your current directory** (`${PWD}`) to `/data`. Since you're currently **inside** `dssat-csm-data-develop/`, that's what gets mounted to `/data`, not the parent project directory.

**Result:** `/data/StrawberryDockerCreate1.v48` creates the file directly in your current `dssat-csm-data-develop/` directory, which is exactly what you want!

### 4. Running Python Scripts

#### Navigate to Project Root

```bash
cd /mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main
```

#### Run Individual Python Scripts

```bash
# 1. Main strawberry model implementation
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /app/cropgro-strawberry-implementation.py

# 2. Test the strawberry model
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /app/cropgro-strawberry-test1.py

# 3. Compare Python vs Fortran implementations
# Must cd to local CN-strawberryDSSAT-main/dssat-csm-data-develop first
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /data/enhanced_compare_with_fortran.py /data/dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir /data/dssat-csm-os-develop

# 4. Run original DSSAT model
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /data/run_original_dssat.py /data/dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir /data/dssat-csm-os-develop

# 5. Validate models against DSSAT
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /data/validate_models.py /data/dssat-csm-data-develop/Strawberry/UFBA1601.SRX --dssat-dir /data/dssat-csm-os-develop --tolerance 1.0

# 6. Run all comparisons
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /app/run_all_comparisons.py

# 7. Explain result differences
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /app/explain_row_differences.py

# 8. Show dataframe details
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 ./show_dataframe_details.py
```

### 5. Interactive Analysis Session

```bash
# Start interactive Python session
docker run --rm -it -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest

# Inside the container:
# Activate Python virtual environment (already activated by default) 
source /app/venv/bin/activate

# Start Python
python3
```

```python
# Import and use modules
import sys
sys.path.append('/app')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Import your strawberry model
exec(open('/app/cropgro-strawberry-implementation.py').read())
```

### 6. File Outputs and Results

#### DSSAT Outputs (in Strawberry/ directory)

- **Summary.OUT** - Overall simulation results
- **PlantGro.OUT** - Detailed plant growth data
- **FreshWt.OUT** - Fresh weight over time
- **OVERVIEW.OUT** - Comprehensive simulation overview
- **Weather.OUT** - Weather data used
- **Evaluate.OUT** - Model evaluation statistics

#### Python Script Outputs

- Various CSV files with model results
- Comparison tables between Python and DSSAT models
- Plots and visualizations (if matplotlib output is configured)

### 7. Troubleshooting

#### Check Container Contents

```bash
# List available executables
docker run --rm dssat-strawberry-python-numba2:latest ls -la /app/dssat/

# List Python scripts
docker run --rm dssat-strawberry-python-numba2:latest ls -la /app/*.py

# Check Python environment
docker run --rm dssat-strawberry-python-numba2:latest python3 -c "import numpy, pandas, matplotlib; print('All packages working!')"
```

#### Debug Mode

```bash
# Start container with bash for debugging
docker run --rm -it -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /bin/bash

# Inside container, you can:
# - Check file permissions
# - Verify paths
# - Run commands step by step
```

## Summary

This Docker image provides a complete environment for:

1. **Running native DSSAT strawberry simulations** using the Fortran executable
2. **Executing Python-based strawberry models** for comparison and analysis
3. **Performing validation studies** between different model implementations
4. **Batch processing** multiple experiments and scenarios

The image ensures reproducible results across different systems while maintaining the proven DSSAT functionality alongside modern Python data analysis capabilities.

## Running Strawberry DSSAT Without Docker

If you want to run DSSAT strawberry simulations directly on your system without Docker, you need to ensure all required files and dependencies are properly set up.

### Required Files and Directory Structure

#### 1. Experiment Data Files (in Strawberry folder)
**Location:** `CN-strawberryDSSAT-main/dssat-csm-data-develop/Strawberry/`

Required files:
- **Weather files (.WTH)** - Climate data for the simulation location
- **Soil files (.SOL)** - Soil profile and characteristics data
- **Experiment files (.SRX)** - Strawberry experiment definitions
  - Example: `UFBA1401.SRX`, `UFBA1601.SRX`, `UFBA1701.SRX`

#### 2. Standard Data Files
**Primary Location:** `CN-strawberryDSSAT-main/dssat-csm-os-develop/Data/StandardData/`
**Alternative Location:** `/usr/local/` (if DSSAT installed system-wide)

Required files:
- **.WDA files** - Standard weather data definitions
- **.SDA files** - Standard soil data definitions

#### 3. Genotype Data Files
**Location:** `CN-strawberryDSSAT-main/dssat-csm-os-develop/Data/Genotype/`

Required files:
- **.CUL files** - Cultivar-specific parameters
- **.ECO files** - Ecotype parameters
- **.SPE files** - Species-specific parameters

#### 4. DSSAT Executable
**Location:** `CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048`

This is the main DSSAT executable that runs the crop simulation models.

#### 5. Run Utility Script
**Location:** `CN-strawberryDSSAT-main/dssat-csm-os-develop/Utilities/run_dssat`

This utility script helps run DSSAT with proper path configurations.

### Prerequisites

1. **Build DSSAT executable** (if not already built):
   ```bash
   cd CN-strawberryDSSAT-main/dssat-csm-os-develop
   mkdir -p build
   cd build
   cmake ..
   make
   ```

2. **Verify executable exists**:
   ```bash
   ls -la CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048
   ```

### Running Strawberry DSSAT Simulations

#### Method 1: Using run_dssat Utility (Recommended)

1. **Navigate to the DSSAT source directory**:
   ```bash
   cd CN-strawberryDSSAT-main/dssat-csm-os-develop
   ```

2. **Run single experiment**:
   ```bash
   ./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1601.SRX
   ```

3. **Run other experiments**:
   ```bash
   # Balm 2014 experiment
   ./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1401.SRX
   
   # Balm 2017 experiment  
   ./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1701.SRX
   ```

**How run_dssat works:**
- The `run_dssat` script internally calls the `dscsm048` executable
- It automatically adds the "A" parameter (meaning run single experiment file)
- It handles path resolution to find the executable and data files
- Command internally executed: `dscsm048 A experiment_file.SRX`

#### Method 2: Direct Executable Usage

1. **Navigate to experiment directory**:
   ```bash
   cd CN-strawberryDSSAT-main/dssat-csm-data-develop/Strawberry
   ```

2. **Run DSSAT directly**:
   ```bash
   # Using relative path to executable
   ../../dssat-csm-os-develop/build/bin/dscsm048 A UFBA1601.SRX
   
   # Or using absolute path
   /full/path/to/CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048 A UFBA1601.SRX
   ```

### Command Parameters Explanation

- **`dscsm048`** - Main DSSAT executable
- **`A`** - Run mode parameter (A = single experiment, B = batch mode)
- **`UFBA1601.SRX`** - Experiment file to execute

### Expected Output Files

After successful execution, DSSAT will generate output files in the experiment directory:
- `Summary.OUT` - Overall simulation results summary
- `PlantGro.OUT` - Detailed daily plant growth data
- `FreshWt.OUT` - Fresh weight development over time
- `OVERVIEW.OUT` - Comprehensive simulation overview
- `Weather.OUT` - Weather data used in simulation
- `Evaluate.OUT` - Model evaluation statistics

### Troubleshooting

#### Common Issues:

1. **Executable not found**:
   ```bash
   # Check if dscsm048 exists and is executable
   ls -la CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048
   chmod +x CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048
   ```

2. **run_dssat script not executable**:
   ```bash
   chmod +x CN-strawberryDSSAT-main/dssat-csm-os-develop/Utilities/run_dssat
   ```

3. **Missing data files**:
   ```bash
   # Verify all required files exist
   ls -la CN-strawberryDSSAT-main/dssat-csm-data-develop/Strawberry/UFBA1601.SRX
   ls -la CN-strawberryDSSAT-main/dssat-csm-os-develop/Data/StandardData/
   ls -la CN-strawberryDSSAT-main/dssat-csm-os-develop/Data/Genotype/
   ```

4. **Path configuration in run_dssat**:
   - Edit `CN-strawberryDSSAT-main/dssat-csm-os-develop/Utilities/run_dssat`
   - Ensure it points to the correct `dscsm048` executable path
   - Verify data directory paths are correctly configured

### Batch Processing

To run multiple experiments in batch mode:

1. **Create or modify batch file** (e.g., `Strawberry.v48`):
   ```
   $BATCH(Strawberry)
   
   @N R O C TNAME...................... NYERS TITL
   !@N R O C TNAME...................... NYERS TITL
    1 1 1 0 BALM-STRAWBERRY-2014              1 DSSAT Test
    2 1 1 0 BALM-STRAWBERRY-2016              1 DSSAT Test  
    3 1 1 0 BALM-STRAWBERRY-2017              1 DSSAT Test
   ```

2. **Run batch processing**:
   ```bash
   cd CN-strawberryDSSAT-main/dssat-csm-data-develop
   ../dssat-csm-os-develop/build/bin/dscsm048 B Strawberry.v48
   ```

This native approach gives you full control over DSSAT execution while avoiding Docker overhead, ideal for development, debugging, or integration into existing workflows.