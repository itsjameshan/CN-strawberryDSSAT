# Developer Guide
# 开发者指南

This repository contains a Python implementation of the DSSAT strawberry model along with scripts to build and compare the official Fortran version. Use this guide to keep contributions consistent.
本仓库包含 DSSAT 草莓模型的 Python 实现，以及用于构建和对比官方 Fortran 版本的脚本。请使用本指南以保持贡献的一致性。

## Environment
## 环境

- Python 3.8+.
- Python 3.8 及以上版本。
- Install requirements with `pip install -r requirements.txt`.
- 使用 `pip install -r requirements.txt` 安装依赖包。
- Fortran code can be built using scripts in `scripts/`.
- 可以使用 `scripts/` 目录下的脚本来编译 Fortran 代码。

## Running the Python model
## 运行 Python 模型

```bash
python cropgro-strawberry-implementation.py
```
```bash
python cropgro-strawberry-implementation.py
```

Use the bundled synthetic weather data or adjust the script for your dataset.
可以使用自带的合成天气数据，也可以根据你的数据集调整脚本。

## Building and running DSSAT
## 构建并运行 DSSAT

- **macOS**: `bash scripts/build_dssat_macos.sh`
- **macOS**: `bash scripts/build_dssat_macos.sh`
- **Windows**: `scripts\build_dssat_windows.cmd`
- **Windows**: `scripts\build_dssat_windows.cmd`
- Run a compiled DSSAT executable using `python run_original_dssat.py path/to/experiment.SRX`.
- 使用 `python run_original_dssat.py path/to/experiment.SRX` 运行编译后的 DSSAT 可执行文件。

## Comparing outputs
## 输出对比

- `python validate_models.py ./dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir dssat-csm-os-develop --tolerance 1.0` checks the Python results against the Fortran model. 检查 Python 结果与 Fortran 模型的对比情况。
- `python validate_models.py ./dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir dssat-csm-os-develop --tolerance 1.0` generates a small report of differences. 生成差异的小报告。


## Tests
## 测试

Run the unit tests before committing:
在提交前运行单元测试：

```bash
python cropgro-strawberry-test1.py
```
```bash
python cropgro-strawberry-test1.py
```

## Commit messages
## 提交信息

Use concise, imperative descriptions (e.g. "Add validation script" or "Fix growth rate calculation"). If a change touches the model logic, note any effects on the outputs.
请使用简洁、命令式的描述（例如 “Add validation script” 或 “Fix growth rate calculation”）。如果更改涉及模型逻辑，请注明对输出的影响。

## Documentation
## 文档

Additional details are found in `docs/student_guide.md` and the project `README.md`.
更多详细信息见 `docs/student_guide.md` 和项目的 `README.md` 文件。
