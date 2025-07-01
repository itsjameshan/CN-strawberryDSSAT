# DSSAT-Strawberry-Python Docker Image Guide
#Build image first
docker build . -f dssat-docker-master/Dockerfile.minimal-python -t dssat-strawberry-python-numba2
  Overview

  This guide documents the dssat-strawberry-python-numba2 Docker image that
  combines DSSAT (Decision Support System for Agrotechnology Transfer)
  with Python environment for running strawberry crop simulations and
  analysis.

  Image Information

  - Image Name: dssat-strawberry-python-numba2
  - Image ID: 0efbd830c067
  - Tag: latest

  Involved Scripts and Files

  1. Docker Configuration Files

  dssat-docker-master/Dockerfile.minimal-python - Main Dockerfile
  - Multi-stage build combining DSSAT + Python
  - Stage 1: Builds DSSAT from Fortran source code
  - Stage 2: Creates Python environment with minimal packages
  - Sets up environment paths for both DSSAT and Python

  dssat-docker-master/local.Dockerfile - Original DSSAT-only reference        
  - Base Dockerfile for DSSAT compilation only
  - Used as reference for the extended version

  2. Python Dependencies

  requirements.txt - Minimal Python packages
  numpy>=1.19.0
  pandas>=1.3.0
  matplotlib>=3.3.0
  numba

  3. Python Scripts (8 files included in image)

  1. cropgro-strawberry-implementation.py - Main CROPGRO-Strawberry model     
   implementation in Python
  2. cropgro-strawberry-test1.py - Test script for the strawberry model       
  3. compare_with_fortran.py - Comparison tool between Python and Fortran     
   versions
  4. run_original_dssat.py - Helper script to run original DSSAT
  strawberry model
  5. validate_models.py - Validation script to compare Python model
  against DSSAT
  6. run_all_comparisons.py - Batch comparison runner for multiple
  scenarios
  7. explain_row_differences.py - Analysis tool for examining result
  differences
  8. show_dataframe_details.py - Data analysis utilities for output
  examination

  4. DSSAT Source Code

  dssat-docker-master/src/ directory contains:
  - Complete DSSAT Fortran source code
  - CMakeLists.txt for compilation
  - Plant models (Plant/ directory)
  - Soil models (Soil/ directory)
  - Weather modules (Weather/ directory)
  - Input/Output modules
  - Utilities and helper functions

  Step-by-Step Usage Guide

  1. Basic Image Information

  # Check image exists
  docker images | grep dssat-strawberry-python-numba2

  # Inspect image details
  docker inspect dssat-strawberry-python-numba2:latest

  2. Running the Docker Container

  Interactive Mode (Recommended for testing)

  # Start interactive container with current directory mounted
  docker run --rm -it -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest

  # Inside container, you'll have access to:
  # - /app/dssat/dscsm048 (DSSAT executable)
  # - /app/*.py (Python scripts)
  # - Python environment with numpy, pandas, matplotlib

  Non-Interactive Mode

  # Run specific commands directly
  docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python:latest [COMMAND]

  3. Running DSSAT Strawberry Experiments

  Navigate to Strawberry Data Directory First

  # Ensure you're in the strawberry experiments directory
  cd dssat-csm-data-develop/Strawberry

  # 验证文件存在
  ls -la UFBA1401.SRX

  Run Individual Strawberry Experiments

  # Balm 2014 experiment
  docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1401.SRX
  docker run --rm -v ${PWD}:/data -w /data/dssat-csm-data-develop/Strawberry dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1401.SRX

  # Balm 2016 experiment
  docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1601.SRX
  docker run --rm -v ${PWD}:/data -w /data/dssat-csm-data-develop/Strawberry dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1601.SRX

  # Balm 2017 experiment
  docker run --rm -v ${PWD}:/data -w /data/dssat-csm-data-develop/Strawberry dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1701.SRX

  Expected DSSAT Output

  RUN    TRT FLO MAT TOPWT HARWT  RAIN  TIRR   CET  PESW  TNUP  TNLF
  TSON TSOC
             dap dap kg/ha kg/ha    mm    mm    mm    mm kg/ha kg/ha
  kg/ha t/ha
    1 SR   1  23 -99  1804    52   -99     0   -99   -99     0   -99
   0   26

  Run Batch Strawberry Experiments

  # First create batch file (if not exists)
  cd ../  # Go to dssat-csm-data-develop directory

  # Create Docker-compatible batch file using the working version
  
  docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest bash -c "sed 's|C:\\\\DSSAT48\\\\Strawberry\\\\|/data/Strawberry/|g' /app/dssat/BatchFiles/Strawberry.v48 > /data/dssat-csm-data-develop/StrawberryDockerCreate1.v48"

  # Run batch experiments
  # Must cd to local CN-strawberryDSSAT-main/dssat-csm-data-develop first
  docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 B StrawberryDocker_duan.v48


### Explain the mount path:
 Let me explain the path mapping when you're in the `dssat-csm-data-develop/` directory:

## **Path Mapping Explanation:**

**Your current location:**
```
/mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main/dssat-csm-data-develop/
```

**When you run:** `-v ${PWD}:/data`

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

## **Visual Example:**

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

## **Key Point:**
Docker always mounts **your current directory** (`${PWD}`) to `/data`. Since you're currently **inside** `dssat-csm-data-develop/`, that's what gets mounted to `/data`, not the parent project directory.

**Result:** `/data/StrawberryDockerCreate1.v48` creates the file directly in your current `dssat-csm-data-develop/` directory, which is exactly what you want!
  
  ######
  4. Running Python Scripts

  Navigate to Project Root

  ### cd /mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main

  Run Individual Python Scripts

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
  

  5. Interactive Analysis Session

  # Start interactive Python session
  docker run --rm -it -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest

  # Inside the container:
  # Activate Python virtual environment (already activated by default)        
  source /app/venv/bin/activate

  # Start Python
  python3

  # Import and use modules
  import sys
  sys.path.append('/app')
  import numpy as np
  import pandas as pd
  import matplotlib.pyplot as plt

  # Import your strawberry model
  exec(open('/app/cropgro-strawberry-implementation.py').read())

  6. File Outputs and Results

  DSSAT Outputs (in Strawberry/ directory)

  - Summary.OUT - Overall simulation results
  - PlantGro.OUT - Detailed plant growth data
  - FreshWt.OUT - Fresh weight over time
  - OVERVIEW.OUT - Comprehensive simulation overview
  - Weather.OUT - Weather data used
  - Evaluate.OUT - Model evaluation statistics

  Python Script Outputs

  - Various CSV files with model results
  - Comparison tables between Python and DSSAT models
  - Plots and visualizations (if matplotlib output is configured)

  7. Troubleshooting

  Check Container Contents

  # List available executables
  docker run --rm dssat-strawberry-python-numba2:latest ls -la /app/dssat/

  # List Python scripts
  docker run --rm dssat-strawberry-python-numba2:latest ls -la /app/*.py

  # Check Python environment
  docker run --rm dssat-strawberry-python-numba2:latest python3 -c "import numpy, pandas, matplotlib; print('All packages working!')"

  Debug Mode

  # Start container with bash for debugging
  docker run --rm -it -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /bin/bash

  # Inside container, you can:
  # - Check file permissions
  # - Verify paths
  # - Run commands step by step

  Summary

  This Docker image provides a complete environment for:
  1. Running native DSSAT strawberry simulations using the Fortran
  executable
  2. Executing Python-based strawberry models for comparison and analysis     
  3. Performing validation studies between different model
  implementations
  4. Batch processing multiple experiments and scenarios

  The image ensures reproducible results across different systems while       
  maintaining the proven DSSAT functionality alongside modern Python data     
   analysis capabilities.