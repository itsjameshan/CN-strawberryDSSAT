
# CROPGRO-Strawberry Model
# CROPGRO-草莓模型

This repository contains a Python implementation of the CROPGRO-Strawberry crop model adapted from the DSSAT framework. The model simulates strawberry growth and development in response to daily weather conditions, soil properties and cultivar characteristics.
本仓库包含了一个基于DSSAT框架改编的CROPGRO-草莓作物模型的Python实现。该模型可根据每日气象条件、土壤性质和品种特性，模拟草莓的生长和发育。

## Key Inputs
## 主要输入

- **Geographic information**
  - Latitude for daylength calculation
  - Planting date
- **地理信息**
  - 用于计算日长的纬度
  - 种植日期

- **Soil properties**
  - Maximum root depth (cm)
  - Field capacity (mm/m)
  - Wilting point (mm/m)
- **土壤性质**
  - 最大根系深度（厘米）
  - 田间持水量（毫米/米）
  - 萎蔫点（毫米/米）

- **Cultivar parameters**
  - Base temperature (°C)
  - Optimal temperature (°C)
  - Maximum threshold temperature (°C)
  - Radiation use efficiency (g/MJ)
  - Light extinction coefficient
  - Specific leaf area (m²/g)
  - Potential fruits per crown
- **品种参数**
  - 基本温度（摄氏度）
  - 最适温度（摄氏度）
  - 最高阈值温度（摄氏度）
  - 辐射利用效率（克/兆焦）
  - 光衰减系数
  - 叶面积比（平方米/克）
  - 每株可能结果数

- **Daily weather data**
  - Maximum and minimum temperatures (°C)
  - Solar radiation (MJ/m²)
  - Rainfall (mm)
  - Relative humidity (%)
  - Wind speed (m/s)
- **每日气象数据**
  - 最高和最低气温（摄氏度）
  - 太阳辐射（兆焦/平方米）
  - 降雨量（毫米）
  - 相对湿度（百分比）
  - 风速（米/秒）

## Key Outputs
## 主要输出

- **Plant growth metrics**
  - Total plant biomass (g/plant)
  - Organ-specific biomass
  - Leaf area index (m²/m²)
  - Root depth (cm)
- **植物生长指标**
  - 植株总生物量（克/株）
  - 各器官生物量
  - 叶面积指数（平方米/平方米）
  - 根系深度（厘米）

- **Reproductive development**
  - Fruit number (fruits/plant)
  - Fruit biomass (g/plant)
  - Crown number (crowns/plant)
  - Runner number (runners/plant)
- **生殖发育**
  - 果实数量（个/株）
  - 果实生物量（克/株）
  - 冠数（冠/株）
  - 匍匐茎数（条/株）

- **Physiological processes**
  - Phenological stage
  - Accumulated thermal time (degree-days)
  - Daily photosynthesis rate
  - Transpiration rate
  - Water stress factor
- **生理过程**
  - 物候期
  - 积温（℃·天）
  - 日光合作用速率
  - 蒸腾速率
  - 水分胁迫因子

- **Time series data**
  - Daily values for all plant state variables
  - Progress through development stages
- **时序数据**
  - 所有植株状态变量的每日值
  - 发育阶段的进展

## Setup
## 安装设置

Requirements:
所需环境：

- Python 3
- `numpy`
- `pandas`
- `matplotlib`

Install the dependencies using `requirements.txt`:
使用 `requirements.txt` 文件安装依赖包：

```bash
pip install -r requirements.txt
```

## Running the example
## 运行示例

Execute the model with the bundled synthetic weather data:
使用内置的合成气象数据运行模型：

```bash
python cropgro-strawberry-implementation.py
```

The script prints final statistics and displays plots of simulated growth.
脚本会输出最终统计结果，并显示模拟生长曲线图。

## Running the tests
## 运行测试

A unit test suite is provided. Run it with:
已提供单元测试套件。运行如下：

```bash
python cropgro-strawberry-test1.py
```

## Running the original DSSAT code
## 运行原始DSSAT代码

The repository also includes the full Fortran source of DSSAT in the `dssat-csm-os-develop` directory. Build it using CMake:
本仓库还包含了DSSAT的完整Fortran源代码，位于 `dssat-csm-os-develop` 目录。可通过CMake进行编译：

```bash
cd dssat-csm-os-develop
mkdir build
cd build
cmake ..
make
```

After compilation the `run_dssat` helper script is generated in `Utilities`. Invoke it with a Strawberry `.SRX` experiment file:
编译后，`Utilities` 目录下会生成 `run_dssat` 辅助脚本。用草莓实验文件（.SRX）调用它：

```bash
./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1601.SRX
```

### Building on macOS
### 在macOS上编译

Install `cmake` and `gcc` (providing `gfortran`), for example via Homebrew:
安装 `cmake` 和 `gcc`（包含 `gfortran`），可通过Homebrew安装：

```bash
brew install cmake gcc
```

Run the helper script to compile and install DSSAT. The script also copies the
sample strawberry experiments and weather files, generates a `STRB.V48` batch
file, and executes the model, writing results to `/usr/local/BatchFiles`:
运行辅助脚本以编译和安装DSSAT。脚本还会复制草莓实验和气象文件，生成 `STRB.V48` 批处理文件，并执行模型，将结果写入 `/usr/local/BatchFiles` 目录：

```bash
./scripts/build_dssat_macos.sh
```

### Building on Windows
### 在Windows上编译

Install CMake and a gfortran toolchain such as MinGW-w64. The Windows batch file
performs the same actions as the macOS script: build, install, stage the
strawberry data and run the simulation. Execute it from a Windows terminal:
安装CMake和gfortran工具链（如MinGW-w64）。Windows批处理文件的作用与macOS脚本一致：编译、安装、准备草莓数据并运行模拟。在Windows终端中执行：

```cmd
scriptsuild_dssat_windows.cmd
```

`build_dssat_windows.cmd` is a Windows batch file that relies on the `cmd.exe`
shell and Windows-specific commands such as `xcopy` and `mingw32-make`. A macOS
terminal doesn’t provide these commands or the Windows environment expected by
the script. Instead, macOS users should run the companion script
`scripts/build_dssat_macos.sh`, which performs the same setup using standard
Unix tools. To run the Windows batch file on macOS you’d need a Windows
environment (e.g., a VM or Wine).
`build_dssat_windows.cmd` 是一个基于 `cmd.exe` 的Windows批处理文件，依赖于 `xcopy` 和 `mingw32-make` 等Windows命令。macOS终端没有这些命令，也不具备脚本所需的Windows环境。macOS用户应运行对应的`scripts/build_dssat_macos.sh`脚本，它使用标准Unix工具完成相同设置。如果要在macOS上运行Windows批处理文件，需要使用Windows环境（如虚拟机或Wine）。

## Comparing with the Fortran DSSAT model
## 与Fortran DSSAT模型对比

To verify the Python implementation against the official Fortran code, use `compare_with_fortran.py` or `validate_models.py`. The scripts require a compiled DSSAT installation containing `Utilities/run_dssat`.
要验证Python实现与官方Fortran代码的一致性，可使用 `compare_with_fortran.py` 或 `validate_models.py`。此脚本需要已编译好的DSSAT，并包含 `Utilities/run_dssat`。

```bash

python compare_with_fortran.py dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir dssat-csm-os-develop
```

## Automated validation
## 自动化验证

Use `validate_models.py` to automatically run the official DSSAT executable and the Python implementation, then compare their outputs. The script writes a simple report listing the maximum difference for each common column and whether the results are within the specified tolerance.
使用 `validate_models.py` 可自动运行官方DSSAT和Python实现，并对比其输出。脚本会生成简要报告，列出每个共有变量的最大差异及结果是否在设定容差范围内。

```bash
python validate_models.py ./dssat-csm-data-develop/Strawberry/UFBA1601.SRX --dssat-dir dssat-csm-os-develop --tolerance 1.0
```

See [docs/student_guide.md](docs/student_guide.md) for a concise, step-by-step guide to running the Python model and comparing it with the official DSSAT code.
可参考 [docs/student_guide.md](docs/student_guide.md) 获取简明的分步指南，用于运行Python模型并与官方DSSAT代码对比。

### Full comparison pipeline
### 全流程对比

Run `scripts/run_full_comparison.py` to build DSSAT (if needed) and validate all sample experiments. The script detects your operating system and invokes the appropriate build helper automatically. Reports are saved in `comparison_reports/`.
运行 `scripts/run_full_comparison.py` 可自动编译DSSAT（如有需要）并验证所有样本实验。脚本会自动检测操作系统并调用相应的编译辅助工具。报告保存在 `comparison_reports/` 目录。

```bash
python scripts/run_full_comparison.py
```

After running the pipeline you can visualize the validation summaries with `scripts/plot_results.py`:
运行流程后，可使用 `scripts/plot_results.py` 可视化验证汇总结果：

```bash
python scripts/plot_results.py --reports comparison_reports
```
