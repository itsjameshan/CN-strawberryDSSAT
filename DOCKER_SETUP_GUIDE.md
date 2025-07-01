# 综合 DSSAT + Python Docker 设置指南
# Comprehensive DSSAT + Python Docker Setup Guide

本指南将帮助您使用Docker设置完整的DSSAT + Python环境，包含您原始`improved_setup_script.sh`中的所有功能。

This guide will help you set up a complete DSSAT + Python environment using Docker, including all functionality from your original `improved_setup_script.sh`.

## 🚀 快速开始 / Quick Start

### 前提条件 / Prerequisites

1. **安装Docker / Install Docker**
   - Windows: 下载并安装 [Docker Desktop](https://docker.com)
   - macOS: 下载并安装 [Docker Desktop](https://docker.com)
   - Linux: `sudo apt-get install docker.io` (Ubuntu/Debian)

2. **启动Docker / Start Docker**
   - 确保Docker Desktop正在运行
   - Make sure Docker Desktop is running

3. **磁盘空间 / Disk Space**
   - 至少5GB可用空间用于Docker镜像
   - At least 5GB free space for Docker image

### 一键设置 / One-Click Setup

```bash
# 进入项目目录 / Navigate to project directory
cd /mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main

# 运行完整设置脚本 / Run complete setup script
bash docker_setup_complete.sh
```

这个脚本将自动完成所有设置步骤！
This script will automatically complete all setup steps!

## 📝 详细步骤 / Detailed Steps

### 步骤1：准备文件 / Step 1: Prepare Files

确保您在正确的目录中并且拥有所有必需文件：
Make sure you're in the correct directory and have all required files:

```bash
# 检查当前目录 / Check current directory
ls -la

# 应该看到以下文件 / You should see these files:
# - Dockerfile.comprehensive
# - docker_build.sh
# - docker_run.sh
# - docker_setup_complete.sh
# - dssat-csm-os-develop/
# - dssat-csm-data-develop/
# - requirements.txt
# - cropgro-strawberry-implementation.py
# - 等等... / etc...
```

### 步骤2：构建Docker镜像 / Step 2: Build Docker Image

```bash
# 方法1：使用完整设置脚本（推荐）/ Method 1: Use complete setup script (Recommended)
bash docker_setup_complete.sh

# 方法2：仅构建镜像 / Method 2: Build image only
bash docker_build.sh

# 方法3：手动构建 / Method 3: Manual build
docker build -f Dockerfile.comprehensive -t strawberry-dssat:latest .
```

**注意：** 首次构建需要10-20分钟，取决于网络速度。Docker会使用中国镜像源加速下载。

**Note:** First build takes 10-20 minutes depending on network speed. Docker will use Chinese mirrors for faster downloads.

### 步骤3：运行容器 / Step 3: Run Container

#### 交互式Shell / Interactive Shell
```bash
# 启动交互式容器 / Start interactive container
bash docker_run.sh

# 或者 / Or
bash docker_run.sh --interactive
```

#### Python模型 / Python Model
```bash
# 运行Python草莓模型 / Run Python strawberry model
bash docker_run.sh --python-model

# 运行Python测试 / Run Python tests
bash docker_run.sh --python-tests
```

#### DSSAT模型 / DSSAT Model
```bash
# 运行DSSAT批量实验 / Run DSSAT batch experiments
bash docker_run.sh --dssat-batch

# 运行单个DSSAT实验 / Run single DSSAT experiment
bash docker_run.sh --dssat-single UFBA1601.SRX
```

#### Jupyter Notebook
```bash
# 启动Jupyter服务器 / Start Jupyter server
bash docker_run.sh --jupyter

# 自定义端口 / Custom port
bash docker_run.sh --jupyter 9999

# 然后在浏览器中打开 / Then open in browser:
# http://localhost:8888 (or your custom port)
```

#### 模型对比 / Model Comparison
```bash
# 对比Python vs DSSAT模型 / Compare Python vs DSSAT models
bash docker_run.sh --compare /app/dssat/Strawberry/UFBA1601.SRX

# 验证模型精度 / Validate model accuracy
bash docker_run.sh --validate /app/dssat/Strawberry/UFBA1601.SRX 1.0
```

## 🔧 高级使用 / Advanced Usage

### 自定义命令 / Custom Commands

```bash
# 运行自定义命令 / Run custom command
bash docker_run.sh --custom-cmd "ls -la /app"

# 进入容器查看文件 / Enter container to explore files
bash docker_run.sh --custom-cmd "/bin/bash"
```

### 文件访问 / File Access

您的项目文件在容器中的位置：
Your project files are available in the container at:

- **主机目录** / Host directory: `/mnt/c/Users/cheng/Downloads/CN-strawberryDSSAT-main`
- **容器内路径** / Container path: `/app/host-data`

```bash
# 在容器内访问您的文件 / Access your files inside container
ls /app/host-data
```

### 数据持久化 / Data Persistence

- 容器内的 `/app/host-data` 目录映射到您的本地项目目录
- 所有在此目录中创建的文件都会保存到您的本地计算机
- 容器停止后，其他更改会丢失

- The `/app/host-data` directory in the container maps to your local project directory
- All files created in this directory will be saved to your local computer
- Other changes are lost when the container stops

## 📊 可用的实验文件 / Available Experiment Files

容器包含以下草莓实验文件：
The container includes these strawberry experiment files:

```bash
# 查看可用实验 / View available experiments
bash docker_run.sh --custom-cmd "ls /app/dssat/Strawberry/*.SRX"

# 常用实验文件 / Common experiment files:
# - UFBA1401.SRX
# - UFBA1601.SRX
# - UFBA1701.SRX
# - UFWM1401.SRX
```

## 🛠️ 故障排除 / Troubleshooting

### Docker问题 / Docker Issues

1. **Docker未运行** / Docker not running
   ```bash
   # 检查Docker状态 / Check Docker status
   docker info
   
   # 如果失败，启动Docker Desktop / If fails, start Docker Desktop
   ```

2. **权限问题** / Permission issues
   ```bash
   # Linux: 添加用户到docker组 / Linux: Add user to docker group
   sudo usermod -aG docker $USER
   # 然后重新登录 / Then log out and back in
   ```

3. **磁盘空间不足** / Low disk space
   ```bash
   # 清理Docker镜像 / Clean Docker images
   docker system prune -a
   ```

### 构建问题 / Build Issues

1. **网络连接问题** / Network connectivity issues
   ```bash
   # 重试构建 / Retry build
   bash docker_build.sh --no-clean
   ```

2. **编译错误** / Compilation errors
   ```bash
   # 查看详细日志 / View detailed logs
   cat docker_build.log
   ```

### 运行时问题 / Runtime Issues

1. **容器无法启动** / Container won't start
   ```bash
   # 检查镜像是否存在 / Check if image exists
   docker images strawberry-dssat
   
   # 重新构建 / Rebuild
   bash docker_build.sh
   ```

2. **找不到文件** / Files not found
   ```bash
   # 检查文件挂载 / Check file mounting
   bash docker_run.sh --custom-cmd "ls -la /app/host-data"
   ```

## 📚 完整命令参考 / Complete Command Reference

### 构建命令 / Build Commands
```bash
bash docker_build.sh                    # 完整构建 / Full build
bash docker_build.sh --no-clean         # 构建不清理 / Build without cleanup
bash docker_build.sh --clean-only       # 仅清理 / Cleanup only
bash docker_setup_complete.sh           # 一键设置 / One-click setup
bash docker_setup_complete.sh --build-only  # 仅构建 / Build only
bash docker_setup_complete.sh --test-only   # 仅测试 / Test only
```

### 运行命令 / Run Commands
```bash
bash docker_run.sh                                    # 交互式 / Interactive
bash docker_run.sh --jupyter [port]                   # Jupyter
bash docker_run.sh --python-model                     # Python模型 / Python model
bash docker_run.sh --python-tests                     # Python测试 / Python tests
bash docker_run.sh --dssat-batch                      # DSSAT批量 / DSSAT batch
bash docker_run.sh --dssat-single <file.SRX>          # DSSAT单个 / DSSAT single
bash docker_run.sh --compare <file.SRX>               # 对比模型 / Compare models
bash docker_run.sh --validate <file.SRX> [tolerance]  # 验证模型 / Validate models
bash docker_run.sh --container-help                   # 容器帮助 / Container help
bash docker_run.sh --custom-cmd "<command>"           # 自定义命令 / Custom command
bash docker_run.sh --help                             # 帮助 / Help
```

### 容器内命令 / Commands Inside Container
```bash
/app/run_python_model.sh      # Python模型 / Python model
/app/run_python_tests.sh      # Python测试 / Python tests
/app/run_dssat_batch.sh       # DSSAT批量 / DSSAT batch
/app/run_dssat_single.sh <file>  # DSSAT单个 / DSSAT single
/app/compare_models.sh <file>    # 对比模型 / Compare models
/app/validate_models.sh <file>   # 验证模型 / Validate models
/app/start_jupyter.sh            # Jupyter
/app/help.sh                     # 帮助 / Help
```

## 🎯 使用案例 / Use Cases

### 案例1：运行和测试Python模型 / Case 1: Run and Test Python Model
```bash
# 1. 构建环境 / Build environment
bash docker_setup_complete.sh

# 2. 运行Python模型 / Run Python model
bash docker_run.sh --python-model

# 3. 运行测试 / Run tests
bash docker_run.sh --python-tests
```

### 案例2：使用DSSAT进行批量实验 / Case 2: Batch Experiments with DSSAT
```bash
# 1. 运行所有草莓实验 / Run all strawberry experiments
bash docker_run.sh --dssat-batch

# 2. 运行特定实验 / Run specific experiment
bash docker_run.sh --dssat-single UFBA1601.SRX
```

### 案例3：模型验证和对比 / Case 3: Model Validation and Comparison
```bash
# 1. 对比两个模型 / Compare two models
bash docker_run.sh --compare /app/dssat/Strawberry/UFBA1601.SRX

# 2. 验证精度 / Validate accuracy
bash docker_run.sh --validate /app/dssat/Strawberry/UFBA1601.SRX 0.5
```

### 案例4：数据分析和可视化 / Case 4: Data Analysis and Visualization
```bash
# 1. 启动Jupyter / Start Jupyter
bash docker_run.sh --jupyter

# 2. 在浏览器中打开 / Open in browser
# http://localhost:8888

# 3. 在Jupyter中运行分析 / Run analysis in Jupyter
```

## 🔄 与原始improved_setup_script.sh的对应关系 / Mapping to Original improved_setup_script.sh

Docker解决方案包含了原始脚本的所有功能：
The Docker solution includes all functionality from the original script:

| 原始功能 / Original Feature | Docker对应方案 / Docker Solution |
|----------------------------|----------------------------------|
| Python环境设置 / Python environment setup | ✅ 预装在Docker镜像中 / Pre-installed in Docker image |
| 中国镜像源 / Chinese mirrors | ✅ Docker构建时使用 / Used during Docker build |
| 虚拟环境 / Virtual environment | ✅ 容器即虚拟环境 / Container IS the virtual environment |
| DSSAT编译 / DSSAT compilation | ✅ 预编译在Docker镜像中 / Pre-compiled in Docker image |
| 依赖包安装 / Package installation | ✅ 所有包预装 / All packages pre-installed |
| 代理绕过 / Proxy bypass | ✅ Docker镜像构建时处理 / Handled during Docker image build |
| 错误处理 / Error handling | ✅ 改进的错误处理 / Enhanced error handling |
| 状态跟踪 / State tracking | ✅ Docker镜像是最终状态 / Docker image is final state |

## 📈 优势 / Advantages

相比原始的improved_setup_script.sh，Docker方案提供：
Compared to the original improved_setup_script.sh, the Docker solution provides:

1. **一致性** / Consistency: 在所有系统上相同的环境
2. **可重复性** / Reproducibility: 每次都是相同的设置
3. **隔离性** / Isolation: 不影响主系统
4. **便携性** / Portability: 可以在任何支持Docker的系统上运行
5. **简化** / Simplification: 一次构建，多次使用
6. **无依赖冲突** / No dependency conflicts: 完全隔离的环境

## 🚀 下一步 / Next Steps

1. 运行您的第一个实验！ / Run your first experiment!
2. 探索Jupyter notebooks进行数据分析 / Explore Jupyter notebooks for data analysis
3. 对比Python和DSSAT模型结果 / Compare Python and DSSAT model results
4. 开发自己的模型改进 / Develop your own model improvements

## 💡 提示 / Tips

- 使用 `bash docker_run.sh --help` 查看所有可用选项
- 容器内的更改不会持久化，除非保存在 `/app/host-data`
- 如需帮助，运行 `bash docker_run.sh --container-help`
- Use `bash docker_run.sh --help` to see all available options
- Changes inside the container won't persist unless saved in `/app/host-data`
- For help, run `bash docker_run.sh --container-help`

祝您使用愉快！ / Happy modeling! 🌱