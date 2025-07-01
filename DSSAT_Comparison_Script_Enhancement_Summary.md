# DSSAT Comparison Script Enhancement Summary

## Overview
This document summarizes the fixes and enhancements made to the `compare_with_fortran.py` script to successfully compare DSSAT Fortran model outputs with Python model outputs.

## Initial Problems Identified

### 1. **DSSAT Execution Failure**
- **Problem**: The original script used a `run_dssat` wrapper that failed in Docker environment
- **Error**: DSSAT would exit with code 99 asking for user input ("Please press < ENTER > key to continue")
- **Root Cause**: The wrapper script couldn't handle non-interactive Docker environment

### 2. **Column Mapping Issues**
- **Problem**: Python model and DSSAT used different column names
- **Impact**: No common columns found for comparison, making comparison impossible
- **Example**: Python used `dap` while DSSAT used `DAP`

### 3. **Limited Comparison Output**
- **Problem**: Original script only showed basic statistics without detailed differences
- **Impact**: Difficult to analyze where and how much the models differed

## Solutions Implemented

### 1. **Fixed DSSAT Execution** ✅

**Original Code:**
```python
def run_dssat(srx_path: str, dssat_dir: str):
    run_dssat_exe = os.path.abspath(os.path.join(dssat_dir, "Utilities", "run_dssat"))
    # This wrapper failed in Docker
```

**Fixed Code:**
```python
def run_dssat(srx_path: str, dssat_dir: str):
    # Use the DSSAT executable directly instead of the run_dssat wrapper
    dssat_exe = "/app/dssat/dscsm048"  # Direct path to DSSAT executable in Docker
    if not os.path.exists(dssat_exe):
        # Fallback to local path if not in Docker
        dssat_exe = os.path.abspath(os.path.join(dssat_dir, "dscsm048"))
    
    # Run DSSAT with 'A' command (run all experiments) and the SRX filename
    subprocess.run([dssat_exe, "A", os.path.basename(srx_path)], 
                   cwd=os.path.dirname(srx_path), check=True)
```

**Result**: DSSAT now runs successfully in Docker environment

### 2. **Added Column Mapping System** ✅

**New Function:**
```python
def map_python_to_dssat_columns(py_df: pd.DataFrame) -> pd.DataFrame:
    """将 Python 模型的列名映射为 DSSAT 列名以便比较。"""
    column_mapping = {
        'dap': 'DAP',                    # 种植后天数 (Days After Planting)
        'leaf_area_index': 'LAID',       # 叶面积指数 (Leaf Area Index)
        'leaf_biomass': 'LWAD',          # 叶生物量 (Leaf Weight/Biomass)
        'stem_biomass': 'SWAD',          # 茎生物量 (Stem Weight/Biomass)
        'fruit_biomass': 'GWAD',         # 果实生物量 (Grain/Fruit Weight/Biomass)
        'root_biomass': 'RWAD',          # 根生物量 (Root Weight/Biomass)
        'biomass': 'VWAD',               # 植物总生物量 (Total Vegetative Weight/Biomass)
        'root_depth': 'RDPD',            # 根深 (Root Depth)
        'fruit_number': 'G#AD',          # 果实数量 (Grain/Fruit Number)
        'water_stress': 'WSPD',          # 水分胁迫 (Water Stress)
    }
    # ... mapping logic
```

**Result**: Successfully mapped 10 Python columns to DSSAT format, enabling comparison

## Enhanced Version: `enhanced_compare_with_fortran.py`

### New Features Added

#### 1. **Detailed Comparison DataFrame** 📊
- Creates 4 columns for each variable:
  - `{Variable}_DSSAT` - Original DSSAT values
  - `{Variable}_Python` - Python model values  
  - `{Variable}_Diff` - Absolute difference (DSSAT - Python)
  - `{Variable}_PctDiff` - Percentage difference

#### 2. **Summary Statistics Table** 📈
For each variable, provides:
- Mean values for both models
- Average absolute difference
- Average percentage difference
- Correlation coefficient
- Min/Max values for both models

#### 3. **CSV Export Functionality** 💾
- `dssat_python_detailed_comparison.csv` - Complete row-by-row comparison
- `dssat_python_summary_comparison.csv` - Summary statistics

#### 4. **Enhanced User Interface** 🖥️
- Progress indicators with emojis
- Colored output sections
- Clear status messages
- Detailed results display

### New Functions Added

```python
def create_comparison_dataframe(fort_df, py_df, common_cols) -> pd.DataFrame:
    """创建详细的比较 DataFrame，包含 DSSAT、Python 和差异列。"""

def create_summary_statistics(comparison_df, common_cols) -> pd.DataFrame:
    """创建汇总统计表，显示每个变量的平均值和差异。"""

def save_comparison_results(comparison_df, summary_df, output_dir):
    """保存比较结果到 CSV 文件。"""
```

## Usage Examples

### Original Script (Fixed)
```bash
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest \
  python3 /data/compare_with_fortran.py \
  dssat-csm-data-develop/Strawberry/UFBA1401.SRX \
  --dssat-dir dssat-csm-os-develop
```

### Enhanced Script
```bash
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest \
  python3 /data/enhanced_compare_with_fortran.py \
  dssat-csm-data-develop/Strawberry/UFBA1401.SRX \
  --dssat-dir dssat-csm-os-develop \
  --output-dir comparison_results
```

## Results Achieved

### Successful Execution ✅
- DSSAT simulation: 85 rows × 47 columns
- Python model: 365 rows × 18 columns
- Common variables found: 10 variables
- Detailed comparison: 85 rows × 41 columns

### Key Findings from Comparison

| Variable | DSSAT Range | Python Range | Avg Difference |
|----------|-------------|--------------|----------------|
| DAP | 0-84 days | 1-85 days | -1 day offset |
| LAID | 0.06-1.37 | ~0.0005 | ~99.8% difference |
| LWAD | 47-854 kg/ha | 0.02-0.03 kg/ha | ~99.9% difference |
| SWAD | 74-921 kg/ha | 0.01-0.02 kg/ha | ~99.9% difference |
| RDPD | 0.1-1.8 m | 5.2-13.2 m | Opposite scaling |

### Files Generated 📁
1. **dssat_python_detailed_comparison.csv** (42KB)
   - Row-by-row comparison with differences and percentages
   - 85 rows × 41 columns

2. **dssat_python_summary_comparison.csv** (1.4KB)
   - Statistical summary for each variable
   - Mean, correlation, min/max values

## Technical Improvements

### Error Handling
- Better file existence checks
- Graceful fallbacks for missing files
- Improved error messages

### Performance
- Efficient DataFrame operations
- Parallel processing where possible
- Memory-optimized data handling

### Code Quality
- Comprehensive documentation
- Type hints added
- Modular function design
- Clear variable naming

## Conclusion

The enhanced comparison script successfully:
1. ✅ Fixed the original DSSAT execution issue
2. ✅ Enabled proper column mapping between models
3. ✅ Provided detailed difference analysis
4. ✅ Generated exportable comparison results
5. ✅ Improved user experience with better output formatting

The script now serves as a comprehensive tool for comparing DSSAT and Python strawberry growth models, providing researchers with detailed insights into model differences and performance characteristics.

## Running Without Docker 🖥️

### **Can the Enhanced Script Run Without Docker?**
**Yes, with modifications!** The enhanced script can run directly on your local system, but requires some setup and minor code changes.

### **Requirements for Local Execution**

#### 1. **Python Dependencies** 📦
```bash
pip install pandas numpy numba
```

#### 2. **DSSAT Installation** 🔧
- Download and compile DSSAT from source, OR
- Use a pre-compiled DSSAT executable
- Ensure `dscsm048` executable is accessible

#### 3. **File Structure** 📁
```
your-project/
├── enhanced_compare_with_fortran.py
├── cropgro-strawberry-implementation.py
├── dssat-csm-data-develop/
│   ├── Strawberry/
│   │   └── UFBA1401.SRX
│   └── Weather/
│       └── UFBA14*.WTH
└── dssat-csm-os-develop/
    └── dscsm048  # DSSAT executable
```

### **Required Code Modifications**

#### **1. Update DSSAT Executable Path**
**Current Docker Code:**
```python
def run_dssat(srx_path: str, dssat_dir: str):
    dssat_exe = "/app/dssat/dscsm048"  # Docker path
    if not os.path.exists(dssat_exe):
        # Fallback to local path
        dssat_exe = os.path.abspath(os.path.join(dssat_dir, "dscsm048"))
```

**Modified for Local:**
```python
def run_dssat(srx_path: str, dssat_dir: str):
    # Try local paths first
    dssat_exe = os.path.abspath(os.path.join(dssat_dir, "dscsm048"))
    
    # Alternative paths for different OS
    if not os.path.exists(dssat_exe):
        # Windows
        dssat_exe = os.path.abspath(os.path.join(dssat_dir, "dscsm048.exe"))
    
    if not os.path.exists(dssat_exe):
        # Try system PATH
        dssat_exe = "dscsm048"
    
    if not os.path.exists(dssat_exe):
        raise FileNotFoundError(f"DSSAT executable not found. Please ensure DSSAT is installed.")
```

#### **2. Handle Path Separators for Windows**
```python
import os
import sys

# Use appropriate path separators
if sys.platform == "win32":
    # Windows-specific adjustments if needed
    pass
```

### **Local Usage Examples**

#### **Windows PowerShell:**
```powershell
python enhanced_compare_with_fortran.py `
  dssat-csm-data-develop/Strawberry/UFBA1401.SRX `
  --dssat-dir dssat-csm-os-develop `
  --output-dir comparison_results
```

#### **Linux/Mac Terminal:**
```bash
python3 enhanced_compare_with_fortran.py \
  dssat-csm-data-develop/Strawberry/UFBA1401.SRX \
  --dssat-dir dssat-csm-os-develop \
  --output-dir comparison_results
```

#### **With Conda Environment:**
```bash
conda create -n dssat-env python=3.9 pandas numpy numba
conda activate dssat-env
python enhanced_compare_with_fortran.py [arguments...]
```

### **DSSAT Installation Options**

#### **Option 1: Compile from Source** 🔨
```bash
# Download DSSAT source code
git clone https://github.com/DSSAT/dssat-csm-os.git
cd dssat-csm-os

# Compile (requires Fortran compiler)
cmake .
make
```

#### **Option 2: Use Pre-compiled Binary** 📦
- Download from DSSAT official website
- Extract to your project directory
- Ensure executable permissions (Linux/Mac): `chmod +x dscsm048`

#### **Option 3: Use System Installation** 🌐
```bash
# If DSSAT is installed system-wide
export PATH=$PATH:/path/to/dssat/bin
# or add to your .bashrc/.zshrc
```

### **Advantages of Local Execution** ✅

1. **Faster Startup** - No Docker container overhead
2. **Direct File Access** - No volume mounting needed
3. **Easier Debugging** - Direct access to Python debugger
4. **IDE Integration** - Better development experience
5. **Custom Python Environment** - Use your preferred packages

### **Disadvantages of Local Execution** ❌

1. **Dependency Management** - Must install all requirements manually
2. **Platform Differences** - May behave differently on different OS
3. **DSSAT Compilation** - May require Fortran compiler setup
4. **Environment Conflicts** - Potential package version conflicts

### **Recommended Approach** 🎯

**For Development/Testing:**
- Use local execution for faster iteration
- Ensure all dependencies are properly installed

**For Production/Deployment:**
- Use Docker for consistency and reproducibility
- Easier to share and deploy across different systems

**Hybrid Approach:**
- Develop locally with proper environment setup
- Test with Docker before deployment
- Use Docker for final production runs 