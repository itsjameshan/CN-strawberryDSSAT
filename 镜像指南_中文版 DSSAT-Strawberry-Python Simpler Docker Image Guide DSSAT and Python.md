# DSSAT-Strawberry-Python Docker镜像指南
#首先构建镜像
docker build . -f dssat-docker-master/Dockerfile.minimal-python -t dssat-strawberry-python-numba2

## 概述

本指南记录了dssat-strawberry-python-numba2 Docker镜像，该镜像结合了DSSAT（农业技术转移决策支持系统）和Python环境，用于运行草莓作物模拟和分析。

## 镜像信息

- 镜像名称: dssat-strawberry-python-numba2
- 镜像ID: 0efbd830c067
- 标签: latest

## 相关脚本和文件

### 1. Docker配置文件

**dssat-docker-master/Dockerfile.minimal-python** - 主要的Dockerfile
- 结合DSSAT + Python的多阶段构建
- 阶段1：从Fortran源码构建DSSAT
- 阶段2：创建包含最小包的Python环境
- 为DSSAT和Python设置环境路径

**dssat-docker-master/local.Dockerfile** - 原始的仅DSSAT参考文件
- 仅用于DSSAT编译的基础Dockerfile
- 用作扩展版本的参考

### 2. Python依赖

**requirements.txt** - 最小Python包
```
numpy>=1.19.0
pandas>=1.3.0
matplotlib>=3.3.0
numba
```

### 3. Python脚本（镜像中包含8个文件）

1. **cropgro-strawberry-implementation.py** - 主要的CROPGRO-Strawberry模型Python实现
2. **cropgro-strawberry-test1.py** - 草莓模型的测试脚本
3. **enhanced_compare_with_fortran.py** - Python和Fortran版本之间的比较工具
4. **run_original_dssat.py** - 运行原始DSSAT草莓模型的辅助脚本
5. **validate_models.py** - 验证Python模型与DSSAT对比的验证脚本
6. **run_all_comparisons.py** - 多种场景的批量比较运行器
7. **explain_row_differences.py** - 检查结果差异的分析工具
8. **show_dataframe_details.py** - 输出检查的数据分析工具

### 4. DSSAT源代码

**dssat-docker-master/src/** 目录包含：
- 完整的DSSAT Fortran源代码
- 用于编译的CMakeLists.txt
- 植物模型（Plant/目录）
- 土壤模型（Soil/目录）
- 气象模块（Weather/目录）
- 输入/输出模块
- 工具和辅助函数

## 分步使用指南

### 1. 基本镜像信息

```bash
# 检查镜像是否存在
docker images | grep dssat-strawberry-python-numba2

# 检查镜像详细信息
docker inspect dssat-strawberry-python-numba2:latest
```

### 2. 运行Docker容器

**交互模式（推荐用于测试）**

```bash
# 启动交互式容器，挂载当前目录
docker run --rm -it -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest

# 在容器内，您可以访问：
# - /app/dssat/dscsm048 (DSSAT可执行文件)
# - /app/*.py (Python脚本)
# - 包含numpy、pandas、matplotlib的Python环境
```

**非交互模式**

```bash
# 直接运行特定命令
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python:latest [命令]
```

### 3. 运行DSSAT草莓实验

**首先导航到草莓数据目录**

```bash
# 确保您在草莓实验目录中
cd dssat-csm-data-develop/Strawberry

# 验证文件存在
ls -la UFBA1401.SRX
```

**运行单个草莓实验**

```bash
# Balm 2014实验
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1401.SRX
docker run --rm -v ${PWD}:/data -w /data/dssat-csm-data-develop/Strawberry dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1401.SRX

# Balm 2016实验
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1601.SRX
docker run --rm -v ${PWD}:/data -w /data/dssat-csm-data-develop/Strawberry dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1601.SRX

# Balm 2017实验
docker run --rm -v ${PWD}:/data -w /data/dssat-csm-data-develop/Strawberry dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 A UFBA1701.SRX
```

**预期的DSSAT输出**

```
RUN    TRT FLO MAT TOPWT HARWT  RAIN  TIRR   CET  PESW  TNUP  TNLF
TSON TSOC
         dap dap kg/ha kg/ha    mm    mm    mm    mm kg/ha kg/ha
kg/ha t/ha
  1 SR   1  23 -99  1804    52   -99     0   -99   -99     0   -99
 0   26
```

**运行批量草莓实验**

```bash
# 首先创建批处理文件（如果不存在）
cd ../  # 进入dssat-csm-data-develop目录

# 使用工作版本创建Docker兼容的批处理文件

docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest bash -c "sed 's|C:\\\\DSSAT48\\\\Strawberry\\\\|/data/Strawberry/|g' /app/dssat/BatchFiles/Strawberry.v48 > /data/dssat-csm-data-develop/StrawberryDockerCreate1.v48"

# 运行批量实验
# 必须先cd到本地CN-strawberryDSSAT-main/dssat-csm-data-develop
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /app/dssat/dscsm048 B StrawberryDocker_duan.v48
```

### 路径映射说明

让我解释一下当您在`dssat-csm-data-develop/`目录中时的路径映射：

**路径映射说明：**

**您的当前位置：**
```
/mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main/dssat-csm-data-develop/
```

**当您运行：** `-v ${PWD}:/data`

**发生的情况：**
- **`${PWD}`** = `/mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main/dssat-csm-data-develop/`
- **Docker挂载：** 这整个目录到容器内的`/data`

**所以映射是：**
```
主机: /mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main/dssat-csm-data-develop/
  ↓
容器: /data/
```

**因此：**
- **`/data/StrawberryDockerCreate1.v48`** （容器内）
- **指向：** `/mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main/dssat-csm-data-develop/StrawberryDockerCreate1.v48` （主机上）

**可视化示例：**

**主机文件系统：**
```
CN-strawberryDSSAT-main/
├── dssat-csm-data-develop/          ← 您在这里 (${PWD})
│   ├── StrawberryDocker_duan.v48
│   └── StrawberryDockerCreate1.v48  ← 文件将在这里创建
└── other-folders/
```

**容器文件系统：**
```
/data/                               ← 从${PWD}挂载
├── StrawberryDocker_duan.v48
└── StrawberryDockerCreate1.v48      ← 这是/data/StrawberryDockerCreate1.v48
```

**关键点：**
Docker总是将**您的当前目录**（`${PWD}`）挂载到`/data`。由于您当前**在**`dssat-csm-data-develop/`内，这就是挂载到`/data`的内容，不是父项目目录。

**结果：** `/data/StrawberryDockerCreate1.v48`直接在您当前的`dssat-csm-data-develop/`目录中创建文件，这正是您想要的！

### 4. 运行Python脚本

**导航到项目根目录**

```bash
cd /mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main
```

**运行单个Python脚本**

```bash
# 1. 主要的草莓模型实现
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /app/cropgro-strawberry-implementation.py

# 2. 测试草莓模型
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /app/cropgro-strawberry-test1.py

# 3. 比较Python与Fortran实现
# 必须先cd到本地CN-strawberryDSSAT-main/dssat-csm-data-develop
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /data/enhanced_compare_with_fortran.py /data/dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir /data/dssat-csm-os-develop

# 4. 运行原始DSSAT模型
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /data/run_original_dssat.py /data/dssat-csm-data-develop/Strawberry/UFBA1401.SRX --dssat-dir /data/dssat-csm-os-develop

# 5. 验证模型与DSSAT对比
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /data/validate_models.py /data/dssat-csm-data-develop/Strawberry/UFBA1601.SRX --dssat-dir /data/dssat-csm-os-develop --tolerance 1.0

# 6. 运行所有比较
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /app/run_all_comparisons.py

# 7. 解释结果差异
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 /app/explain_row_differences.py

# 8. 显示数据框详细信息
docker run --rm -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest python3 ./show_dataframe_details.py
```

### 5. 交互式分析会话

```bash
# 启动交互式Python会话
docker run --rm -it -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest

# 在容器内：
# 激活Python虚拟环境（默认已激活）
source /app/venv/bin/activate

# 启动Python
python3

# 导入和使用模块
import sys
sys.path.append('/app')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 导入您的草莓模型
exec(open('/app/cropgro-strawberry-implementation.py').read())
```

### 6. 文件输出和结果

**DSSAT输出（在Strawberry/目录中）**

- Summary.OUT - 总体模拟结果
- PlantGro.OUT - 详细植物生长数据
- FreshWt.OUT - 随时间变化的鲜重
- OVERVIEW.OUT - 综合模拟概览
- Weather.OUT - 使用的气象数据
- Evaluate.OUT - 模型评估统计

**Python脚本输出**

- 包含模型结果的各种CSV文件
- Python和DSSAT模型之间的比较表
- 图表和可视化（如果配置了matplotlib输出）

### 7. 故障排除

**检查容器内容**

```bash
# 列出可用的可执行文件
docker run --rm dssat-strawberry-python-numba2:latest ls -la /app/dssat/

# 列出Python脚本
docker run --rm dssat-strawberry-python-numba2:latest ls -la /app/*.py

# 检查Python环境
docker run --rm dssat-strawberry-python-numba2:latest python3 -c "import numpy, pandas, matplotlib; print('所有包都工作正常！')"
```

**调试模式**

```bash
# 使用bash启动容器进行调试
docker run --rm -it -v ${PWD}:/data -w /data dssat-strawberry-python-numba2:latest /bin/bash

# 在容器内，您可以：
# - 检查文件权限
# - 验证路径
# - 逐步运行命令
```

## 总结

这个Docker镜像提供了一个完整的环境，用于：
1. 使用Fortran可执行文件运行原生DSSAT草莓模拟
2. 执行基于Python的草莓模型进行比较和分析
3. 在不同模型实现之间进行验证研究
4. 批量处理多个实验和场景

该镜像确保在不同系统间的可重现结果，同时在现代Python数据分析能力旁边保持经过验证的DSSAT功能。

## 不使用Docker运行草莓DSSAT

如果您想直接在系统上运行DSSAT草莓模拟而不使用Docker，您需要确保所有必需的文件和依赖项都已正确设置。

### 必需文件和目录结构

#### 1. 实验数据文件（在Strawberry文件夹中）
**位置：** `CN-strawberryDSSAT-main/dssat-csm-data-develop/Strawberry/`

必需文件：
- **气象文件 (.WTH)** - 模拟位置的气候数据
- **土壤文件 (.SOL)** - 土壤剖面和特征数据
- **实验文件 (.SRX)** - 草莓实验定义文件
  - 示例：`UFBA1401.SRX`、`UFBA1601.SRX`、`UFBA1701.SRX`

#### 2. 标准数据文件
**主要位置：** `CN-strawberryDSSAT-main/dssat-csm-os-develop/Data/StandardData/`
**替代位置：** `/usr/local/`（如果DSSAT已系统级安装）

必需文件：
- **.WDA文件** - 标准气象数据定义
- **.SDA文件** - 标准土壤数据定义

#### 3. 基因型数据文件
**位置：** `CN-strawberryDSSAT-main/dssat-csm-os-develop/Data/Genotype/`

必需文件：
- **.CUL文件** - 品种特异性参数
- **.ECO文件** - 生态型参数
- **.SPE文件** - 物种特异性参数

#### 4. DSSAT可执行文件
**位置：** `CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048`

这是运行作物模拟模型的主要DSSAT可执行文件。

#### 5. 运行工具脚本
**位置：** `CN-strawberryDSSAT-main/dssat-csm-os-develop/Utilities/run_dssat`

这个工具脚本帮助以正确的路径配置运行DSSAT。

### 前提条件

1. **构建DSSAT可执行文件**（如果尚未构建）：
   ```bash
   cd CN-strawberryDSSAT-main/dssat-csm-os-develop
   mkdir -p build
   cd build
   cmake ..
   make
   ```

2. **验证可执行文件存在**：
   ```bash
   ls -la CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048
   ```

### 运行草莓DSSAT模拟

#### 方法1：使用run_dssat工具（推荐）

1. **导航到DSSAT源目录**：
   ```bash
   cd CN-strawberryDSSAT-main/dssat-csm-os-develop
   ```

2. **运行单个实验**：
   ```bash
   ./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1601.SRX
   ```

3. **运行其他实验**：
   ```bash
   # Balm 2014实验
   ./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1401.SRX
   
   # Balm 2017实验  
   ./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1701.SRX
   ```

**run_dssat工作原理：**
- `run_dssat`脚本内部调用`dscsm048`可执行文件
- 它自动添加"A"参数（意思是运行单个实验文件）
- 它处理路径解析以找到可执行文件和数据文件
- 内部执行的命令：`dscsm048 A experiment_file.SRX`

#### 方法2：直接使用可执行文件

1. **导航到实验目录**：
   ```bash
   cd CN-strawberryDSSAT-main/dssat-csm-data-develop/Strawberry
   ```

2. **直接运行DSSAT**：
   ```bash
   # 使用相对路径到可执行文件
   ../../dssat-csm-os-develop/build/bin/dscsm048 A UFBA1601.SRX
   
   # 或使用绝对路径
   /完整/路径/到/CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048 A UFBA1601.SRX
   ```

### 命令参数说明

- **`dscsm048`** - 主要的DSSAT可执行文件
- **`A`** - 运行模式参数（A = 单个实验，B = 批处理模式）
- **`UFBA1601.SRX`** - 要执行的实验文件

### 预期输出文件

成功执行后，DSSAT将在实验目录中生成输出文件：
- `Summary.OUT` - 总体模拟结果摘要
- `PlantGro.OUT` - 详细的每日植物生长数据
- `FreshWt.OUT` - 随时间变化的鲜重发展
- `OVERVIEW.OUT` - 综合模拟概览
- `Weather.OUT` - 模拟中使用的气象数据
- `Evaluate.OUT` - 模型评估统计

### 故障排除

#### 常见问题：

1. **找不到可执行文件**：
   ```bash
   # 检查dscsm048是否存在并可执行
   ls -la CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048
   chmod +x CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048
   ```

2. **run_dssat脚本不可执行**：
   ```bash
   chmod +x CN-strawberryDSSAT-main/dssat-csm-os-develop/Utilities/run_dssat
   ```

3. **缺少数据文件**：
   ```bash
   # 验证所有必需文件存在
   ls -la CN-strawberryDSSAT-main/dssat-csm-data-develop/Strawberry/UFBA1601.SRX
   ls -la CN-strawberryDSSAT-main/dssat-csm-os-develop/Data/StandardData/
   ls -la CN-strawberryDSSAT-main/dssat-csm-os-develop/Data/Genotype/
   ```

4. **run_dssat中的路径配置**：
   - 编辑 `CN-strawberryDSSAT-main/dssat-csm-os-develop/Utilities/run_dssat`
   - 确保它指向正确的`dscsm048`可执行文件路径
   - 验证数据目录路径配置正确

### 批处理

要以批处理模式运行多个实验：

1. **创建或修改批处理文件**（例如，`Strawberry.v48`）：
   ```
   $BATCH(Strawberry)
   
   @N R O C TNAME...................... NYERS TITL
   !@N R O C TNAME...................... NYERS TITL
    1 1 1 0 BALM-STRAWBERRY-2014              1 DSSAT Test
    2 1 1 0 BALM-STRAWBERRY-2016              1 DSSAT Test  
    3 1 1 0 BALM-STRAWBERRY-2017              1 DSSAT Test
   ```

2. **运行批处理**：
   ```bash
   cd CN-strawberryDSSAT-main/dssat-csm-data-develop
   ../dssat-csm-os-develop/build/bin/dscsm048 B Strawberry.v48
   ```

这种原生方法让您完全控制DSSAT执行，同时避免Docker开销，非常适合开发、调试或集成到现有工作流程中。

### 文件结构检查清单

在运行之前，请确保以下文件结构完整：

```
CN-strawberryDSSAT-main/
├── dssat-csm-data-develop/
│   └── Strawberry/
│       ├── UFBA1401.SRX          # 实验文件
│       ├── UFBA1601.SRX          # 实验文件  
│       ├── UFBA1701.SRX          # 实验文件
│       ├── *.WTH                 # 气象文件
│       └── *.SOL                 # 土壤文件
│
└── dssat-csm-os-develop/
    ├── build/bin/dscsm048        # DSSAT可执行文件
    ├── Utilities/run_dssat       # 运行脚本
    ├── Data/
    │   ├── StandardData/
    │   │   ├── *.WDA             # 标准气象数据
    │   │   └── *.SDA             # 标准土壤数据
    │   └── Genotype/
    │       ├── *.CUL             # 品种参数
    │       ├── *.ECO             # 生态型参数
    │       └── *.SPE             # 物种参数
    └── [其他DSSAT源文件]
```

### 运行示例

**完整的运行示例：**

```bash
# 1. 确保在正确的目录
cd /path/to/CN-strawberryDSSAT-main

# 2. 验证文件存在
ls -la dssat-csm-os-develop/build/bin/dscsm048
ls -la dssat-csm-data-develop/Strawberry/UFBA1601.SRX

# 3. 使用run_dssat运行（推荐）
cd dssat-csm-os-develop
./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1601.SRX

# 4. 或者直接使用可执行文件
cd dssat-csm-data-develop/Strawberry
../../dssat-csm-os-develop/build/bin/dscsm048 A UFBA1601.SRX

# 5. 检查输出文件
ls -la *.OUT
```

**典型的成功输出示例：**

```
RUN    TRT FLO MAT TOPWT HARWT  RAIN  TIRR   CET  PESW  TNUP  TNLF
TSON TSOC
         dap dap kg/ha kg/ha    mm    mm    mm    mm kg/ha kg/ha
kg/ha t/ha
  1 SR   1  23 -99  1804    52   -99     0   -99   -99     0   -99
 0   26
```

### 环境变量设置（可选）

为了更方便地运行DSSAT，您可以设置以下环境变量：

```bash
# 设置DSSAT根目录
export DSSAT_ROOT=/path/to/CN-strawberryDSSAT-main/dssat-csm-os-develop

# 设置数据目录
export DSSAT_DATA=/path/to/CN-strawberryDSSAT-main/dssat-csm-data-develop

# 将DSSAT可执行文件添加到PATH
export PATH=$DSSAT_ROOT/build/bin:$PATH

# 现在您可以直接使用dscsm048命令
cd $DSSAT_DATA/Strawberry
dscsm048 A UFBA1601.SRX
```

### 验证安装

运行以下命令来验证您的DSSAT安装是否正确：

```bash
# 1. 检查可执行文件
file CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048

# 2. 运行帮助命令（某些版本支持）
CN-strawberryDSSAT-main/dssat-csm-os-develop/build/bin/dscsm048 -h

# 3. 运行一个简单的测试实验
cd CN-strawberryDSSAT-main/dssat-csm-os-develop
./Utilities/run_dssat ../../dssat-csm-data-develop/Strawberry/UFBA1401.SRX

# 4. 检查是否生成了输出文件
ls -la ../../dssat-csm-data-develop/Strawberry/*.OUT
```

### 与Docker版本的对比

| 特性 | 原生运行 | Docker运行 |
|------|----------|-----------|
| **性能** | 更快，无容器开销 | 稍慢，有容器开销 |
| **设置复杂度** | 需要手动配置环境 | 自动化配置 |
| **可移植性** | 依赖系统环境 | 完全可移植 |
| **调试便利性** | 直接访问文件和进程 | 需要进入容器 |
| **适用场景** | 开发、生产部署 | 快速测试、演示 |
| **依赖管理** | 手动管理 | 自动包含 |

### 推荐使用场景

**选择原生运行当：**
- 需要最佳性能
- 进行模型开发和调试
- 集成到现有工作流程
- 有专门的DSSAT服务器

**选择Docker运行当：**
- 快速开始使用
- 需要在不同系统间保持一致性
- 进行教学或演示
- 不想处理复杂的环境配置

这种方法为您提供了对DSSAT模拟的完全控制，非常适合研究、开发和生产环境使用。无论选择哪种方式，都能有效地运行草莓DSSAT模拟并获得可靠的结果。