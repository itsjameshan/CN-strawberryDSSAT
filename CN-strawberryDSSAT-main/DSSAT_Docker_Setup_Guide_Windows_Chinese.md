# DSSAT Docker 草莓仿真设置指南 (Windows版)

## 🎯 概览 (Overview)
本指南将引导您在 **Windows** 系统上使用Docker设置和运行DSSAT（农业技术转移决策支持系统）进行草莓作物仿真。完成后，您将能够运行单个实验和批量仿真。

*This guide walks you through setting up and running DSSAT (Decision Support System for Agrotechnology Transfer) using Docker for strawberry crop simulations **on Windows**. By the end, you'll be able to run both individual experiments and batch simulations.*

## 📋 前提条件 (Prerequisites)
- Windows 10/11 计算机 (64位) *Windows 10/11 computer (64-bit)*
- 互联网连接用于下载Docker *Internet connection for downloading Docker*
- PowerShell 或命令提示符 *PowerShell or Command Prompt*
- 安装时需要管理员权限 *Administrator privileges for installation*

## 🚀 步骤1: 安装Docker Desktop for Windows

1. 访问 https://www.docker.com/products/docker-desktop/
2. 点击 "Download for Windows" (下载Windows版)
3. 运行 `Docker Desktop Installer.exe` 文件
4. 按照安装向导操作:
   - 如提示，启用WSL 2后端 *Enable WSL 2 backend if prompted*
   - 允许Docker创建快捷方式 *Allow Docker to create shortcuts*
5. 提示时重启计算机 *Restart your computer when prompted*
6. 从开始菜单启动Docker Desktop *Launch Docker Desktop from the Start menu*
7. 完成初始设置教程 *Complete the initial setup tutorial*

### 验证安装 (Verify Installation):
打开PowerShell (`Win + X`, 选择 "Windows PowerShell") 或命令提示符并运行:
*Open PowerShell (`Win + X`, select "Windows PowerShell") or Command Prompt and run:*
```powershell
docker --version
```
您应该看到类似这样的内容: `Docker version 28.2.2, build e6534b4`
*You should see something like: `Docker version 28.2.2, build e6534b4`*

## 🐳 步骤2: 启动Docker Desktop

1. 在开始菜单中搜索 "Docker Desktop"
2. 启动Docker Desktop
3. 等待Docker启动 (您会在系统托盘中看到Docker鲸鱼图标)
4. 托盘图标应显示 "Docker Desktop is running" (Docker Desktop正在运行)

### 验证Docker正在运行 (Verify Docker is Running):
```powershell
docker ps
```
应显示带有标题的空表格 (无错误消息)。
*Should show an empty table with headers (no error messages).*

## 📁 步骤3: 准备DSSAT源文件

### 使用PowerShell (推荐) (Using PowerShell - Recommended):

1. **导航到您的项目目录** (Navigate to your project directory):
   ```powershell
   cd C:\path\to\CN-strawberryDSSAT
   ```
   *将 `C:\path\to\` 替换为您的实际路径 (Replace `C:\path\to\` with your actual path)*

2. **将DSSAT源文件复制到Docker源目录** (Copy DSSAT source files to Docker source directory):
   ```powershell
   Copy-Item -Recurse dssat-csm-os-develop\* dssat-docker-master\src\
   ```

3. **验证文件已复制** (Verify files were copied):
   ```powershell
   Get-ChildItem dssat-docker-master\src\
   ```

### 使用命令提示符 (备选) (Using Command Prompt - Alternative):

1. **导航到您的项目目录** (Navigate to your project directory):
   ```cmd
   cd C:\path\to\CN-strawberryDSSAT
   ```

2. **复制DSSAT源文件** (Copy DSSAT source files):
   ```cmd
   xcopy dssat-csm-os-develop\* dssat-docker-master\src\ /E /I
   ```

3. **验证文件已复制** (Verify files were copied):
   ```cmd
   dir dssat-docker-master\src\
   ```

您应该看到像 `CMakeLists.txt`, `Plant\`, `Soil\` 等文件。
*You should see files like `CMakeLists.txt`, `Plant\`, `Soil\`, etc.*

## 🔨 步骤4: 构建DSSAT Docker镜像

### 使用PowerShell (Using PowerShell):

1. **导航到Docker目录** (Navigate to the Docker directory):
   ```powershell
   cd dssat-docker-master
   ```

2. **构建Docker镜像** (需要5-10分钟) (Build the Docker image - this will take 5-10 minutes):
   ```powershell
   docker build . -f local.Dockerfile -t dssat
   ```

3. **验证镜像已创建** (Verify the image was created):
   ```powershell
   docker images | Select-String "dssat"
   ```

### 使用命令提示符 (Using Command Prompt):

1. **导航到Docker目录** (Navigate to the Docker directory):
   ```cmd
   cd dssat-docker-master
   ```

2. **构建Docker镜像** (Build the Docker image):
   ```cmd
   docker build . -f local.Dockerfile -t dssat
   ```

3. **验证镜像已创建** (Verify the image was created):
   ```cmd
   docker images | findstr "dssat"
   ```

您应该看到: `dssat        latest    [image_id]   [time_ago]   129MB`

## 🧪 步骤5: 测试单个实验运行

### 使用PowerShell (Using PowerShell):

1. **导航到草莓数据目录** (Navigate to the strawberry data directory):
   ```powershell
   cd ..\dssat-csm-data-develop\Strawberry
   ```

2. **测试单个实验** (Test single experiments):

   **测试1 - Balm 2014实验** (Test 1 - Balm 2014 experiment):
   ```powershell
   docker run --rm -v ${PWD}:/data -w /data dssat A UFBA1401.SRX
   ```
   
   **测试2 - Balm 2016实验** (Test 2 - Balm 2016 experiment):
   ```powershell
   docker run --rm -v ${PWD}:/data -w /data dssat A UFBA1601.SRX
   ```
   
   **测试3 - Balm 2017实验** (Test 3 - Balm 2017 experiment):
   ```powershell
   docker run --rm -v ${PWD}:/data -w /data dssat A UFBA1701.SRX
   ```

### 使用命令提示符 (Using Command Prompt):

1. **导航到草莓数据目录** (Navigate to the strawberry data directory):
   ```cmd
   cd ..\dssat-csm-data-develop\Strawberry
   ```

2. **测试单个实验** (Test single experiments):

   **测试1 - Balm 2014实验** (Test 1 - Balm 2014 experiment):
   ```cmd
   docker run --rm -v %cd%:/data -w /data dssat A UFBA1401.SRX
   ```
   
   **测试2 - Balm 2016实验** (Test 2 - Balm 2016 experiment):
   ```cmd
   docker run --rm -v %cd%:/data -w /data dssat A UFBA1601.SRX
   ```
   
   **测试3 - Balm 2017实验** (Test 3 - Balm 2017 experiment):
   ```cmd
   docker run --rm -v %cd%:/data -w /data dssat A UFBA1701.SRX
   ```

### 每个测试的预期输出 (Expected Output for each test):
```
RUN    TRT FLO MAT TOPWT HARWT  RAIN  TIRR   CET  PESW  TNUP  TNLF   TSON TSOC
           dap dap kg/ha kg/ha    mm    mm    mm    mm kg/ha kg/ha  kg/ha t/ha
  1 SR   1  23 -99  1804    52   -99     0   -99   -99     0   -99      0   26
```

### 检查输出文件是否已创建 (Check output files were created):

**PowerShell:**
```powershell
Get-ChildItem *.OUT
```

**命令提示符 (Command Prompt):**
```cmd
dir *.OUT
```

您应该看到像 `PlantGro.OUT`, `Summary.OUT`, `FreshWt.OUT` 等文件。
*You should see files like `PlantGro.OUT`, `Summary.OUT`, `FreshWt.OUT`, etc.*

## 📦 步骤6: 设置批处理

### 使用PowerShell (Using PowerShell):

1. **返回到数据目录** (Navigate back to the data directory):
   ```powershell
   cd ..  # 应该在 dssat-csm-data-develop\ 中 (Should be in dssat-csm-data-develop\)
   ```

2. **从Docker源创建工作批处理文件** (Create a working batch file from the Docker source):
   ```powershell
   (Get-Content ..\dssat-docker-master\src\Data\BatchFiles\Strawberry.v48) -replace 'C:\\DSSAT48\\Strawberry\\', '/data/Strawberry/' | Set-Content StrawberryDocker.v48
   ```

3. **验证批处理文件已创建** (Verify the batch file was created):
   ```powershell
   Get-Content StrawberryDocker.v48 | Select-Object -First 15
   ```

### 使用命令提示符 (Using Command Prompt):

1. **返回到数据目录** (Navigate back to the data directory):
   ```cmd
   cd ..
   ```

2. **创建工作批处理文件** (Create a working batch file):
   ```cmd
   powershell -Command "(Get-Content ..\dssat-docker-master\src\Data\BatchFiles\Strawberry.v48) -replace 'C:\\\\DSSAT48\\\\Strawberry\\\\', '/data/Strawberry/' | Set-Content StrawberryDocker.v48"
   ```

3. **验证批处理文件已创建** (Verify the batch file was created):
   ```cmd
   type StrawberryDocker.v48 | more
   ```

## 🚀 步骤7: 运行批量仿真

### 使用PowerShell (Using PowerShell):

1. **执行批量运行** (Execute the batch run):
   ```powershell
   docker run --rm -v ${PWD}:/data -w /data dssat B StrawberryDocker.v48
   ```

### 使用命令提示符 (Using Command Prompt):

1. **执行批量运行** (Execute the batch run):
   ```cmd
   docker run --rm -v %cd%:/data -w /data dssat B StrawberryDocker.v48
   ```

### 预期输出 (共7个实验) (Expected Output - 7 experiments total):
```
RUN    TRT FLO MAT TOPWT HARWT  RAIN  TIRR   CET  PESW  TNUP  TNLF   TSON TSOC
           dap dap kg/ha kg/ha    mm    mm    mm    mm kg/ha kg/ha  kg/ha t/ha
  1 SR   1  23 -99  1804    52   -99     0   -99   -99     0   -99      0   26
  2 SR   1  24 -99  2785   154   -99     0   -99   -99     0   -99      0   26
  3 SR   2  24 -99  2024   148   -99     0   -99   -99     0   -99      0   26
  4 SR   1  26 -99  1905    83   -99     0   -99   -99     0   -99      0   26
  5 SR   2  26 -99  1913   143   -99     0   -99   -99     0   -99      0   26
  6 SR   1  22 -99  3107   185   -99     0   -99   -99     0   -99      0   26
  7 SR   2  23 164  2717   116   -99     0   -99   -99     0   -99      0   26
```

### 检查所有输出文件 (Check all output files):

**PowerShell:**
```powershell
Get-ChildItem Strawberry\*.OUT
Get-ChildItem Strawberry\*.OUT | Measure-Object -Line
```

**命令提示符 (Command Prompt):**
```cmd
dir Strawberry\*.OUT
```

## 📊 理解结果 (Understanding the Results)

### 关键输出指标 (Key Output Metrics):
- **RUN**: 实验运行编号 *Experiment run number*
- **TRT**: 实验内处理编号 *Treatment number within experiment*
- **FLO**: 开花天数 *Days to flowering*
- **MAT**: 成熟天数 (-99 = 未达到) *Days to maturity (-99 = not reached)*
- **TOPWT**: 地上部总生物量 (kg/ha) *Total above-ground biomass (kg/ha)*
- **HARWT**: 收获重量 (kg/ha) *Harvest weight (kg/ha)*
- **TSON**: 土壤有机氮总量 (kg/ha) *Total soil organic nitrogen (kg/ha)*
- **TSOC**: 土壤有机碳总量 (t/ha) *Total soil organic carbon (t/ha)*

### 重要输出文件 (Important Output Files):
- **Summary.OUT**: 总体仿真结果 *Overall simulation results*
- **PlantGro.OUT**: 详细植物生长数据 *Detailed plant growth data*
- **FreshWt.OUT**: 随时间变化的鲜重 *Fresh weight over time*
- **OVERVIEW.OUT**: 综合仿真概览 *Comprehensive simulation overview*
- **Weather.OUT**: 使用的天气数据 *Weather data used*
- **Evaluate.OUT**: 模型评估统计 *Model evaluation statistics*

## 🔧 命令参考 (Windows) (Command Reference - Windows)

### 单个实验运行 (Individual Experiment Run):

**PowerShell:**
```powershell
# 模板 (Template):
docker run --rm -v ${PWD}:/data -w /data dssat A [EXPERIMENT_FILE.SRX]

# 示例 (Examples):
docker run --rm -v ${PWD}:/data -w /data dssat A UFBA1401.SRX
docker run --rm -v ${PWD}:/data -w /data dssat A UFBA1601.SRX
docker run --rm -v ${PWD}:/data -w /data dssat A UFBA1701.SRX
```

**命令提示符 (Command Prompt):**
```cmd
# 模板 (Template):
docker run --rm -v %cd%:/data -w /data dssat A [EXPERIMENT_FILE.SRX]

# 示例 (Examples):
docker run --rm -v %cd%:/data -w /data dssat A UFBA1401.SRX
docker run --rm -v %cd%:/data -w /data dssat A UFBA1601.SRX
docker run --rm -v %cd%:/data -w /data dssat A UFBA1701.SRX
```

### 批量运行 (Batch Run):

**PowerShell:**
```powershell
docker run --rm -v ${PWD}:/data -w /data dssat B StrawberryDocker.v48
```

**命令提示符 (Command Prompt):**
```cmd
docker run --rm -v %cd%:/data -w /data dssat B StrawberryDocker.v48
```

### Windows特定命令 (Windows-Specific Commands):

**PowerShell:**
```powershell
# 复制文件 (Copy files)
Copy-Item -Recurse source_directory\* destination_directory\

# 列出文件详情 (List files with details)
Get-ChildItem -Name *.OUT

# 计算文件行数 (Count lines in file)
Get-Content filename | Measure-Object -Line

# 查看文件前几行 (View first lines of file)
Get-Content filename | Select-Object -First 15

# 查找文件 (Find files)
Get-ChildItem -Recurse -Name "*pattern*"
```

**命令提示符 (Command Prompt):**
```cmd
# 复制文件 (Copy files)
xcopy source_directory\* destination_directory\ /E /I

# 列出文件 (List files)
dir *.OUT

# 查看文件内容 (View file content)
type filename | more

# 查找文件 (Find files)
dir /S "*pattern*"
```

## 🛠️ 故障排除 (Windows) (Troubleshooting - Windows)

### 问题: "command not found: docker" (命令未找到: docker)
**解决方案 (Solution)**: 
1. Docker Desktop未运行。从开始菜单启动Docker Desktop *Docker Desktop is not running. Start Docker Desktop from Start menu*
2. 检查Docker是否在您的PATH中 (安装后重启终端) *Check if Docker is in your PATH (restart terminal after install)*

### 问题: "Cannot connect to Docker daemon" (无法连接到Docker守护进程)
**解决方案 (Solution)**: 
1. 检查Docker Desktop是否正在运行 (系统托盘中的鲸鱼图标) *Check if Docker Desktop is running (whale icon in system tray)*
2. 等待Docker完全启动 *Wait for Docker to fully start*
3. 尝试重启Docker Desktop *Try restarting Docker Desktop*

### 问题: 复制文件时"拒绝访问" ("Access denied" when copying files)
**解决方案 (Solution)**: 
1. 以管理员身份运行PowerShell或命令提示符 *Run PowerShell or Command Prompt as Administrator*
2. 或使用文件资源管理器手动复制文件 *Or copy files manually using File Explorer*

### 问题: "WSL 2安装不完整" ("WSL 2 installation is incomplete")
**解决方案 (Solution)**: 
1. 从Microsoft Store安装WSL 2 *Install WSL 2 from Microsoft Store*
2. 重启计算机 *Restart computer*
3. 重启Docker Desktop *Restart Docker Desktop*

### 问题: 路径包含空格 (Path contains spaces)
**解决方案 (Solution)**: 
**PowerShell:** 带空格的路径自动工作 *Paths with spaces work automatically*
**命令提示符 (Command Prompt):** 使用引号: `"C:\path with spaces\"`

### 问题: PowerShell执行策略 (PowerShell execution policy)
**解决方案 (Solution)**: 
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 🎯 文件结构概览 (Windows) (File Structure Overview - Windows)

```
CN-strawberryDSSAT\
├── dssat-docker-master\
│   ├── local.Dockerfile        # Docker构建说明 (Docker build instructions)
│   └── src\                    # DSSAT源代码 (复制到此处) (DSSAT source code - copied here)
├── dssat-csm-data-develop\
│   ├── Strawberry\             # 草莓实验文件 (Strawberry experiment files)
│   │   ├── UFBA1401.SRX       # Balm 2014实验 (Balm 2014 experiment)
│   │   ├── UFBA1601.SRX       # Balm 2016实验 (Balm 2016 experiment)
│   │   └── UFBA1701.SRX       # Balm 2017实验 (Balm 2017 experiment)
│   └── StrawberryDocker.v48    # 工作批处理文件 (Working batch file)
└── dssat-csm-os-develop\       # 原始DSSAT源码 (Original DSSAT source)
```

## ✅ 成功检查清单 (Windows) (Success Checklist - Windows)

- [ ] Docker Desktop已安装并运行 (系统托盘中的鲸鱼图标) *Docker Desktop installed and running (whale icon in system tray)*
- [ ] PowerShell/CMD可以成功运行 `docker --version` *PowerShell/CMD can run `docker --version` successfully*
- [ ] DSSAT Docker镜像构建成功 *DSSAT Docker image built successfully*
- [ ] 单个实验运行产生结果 *Individual experiment runs produce results*
- [ ] 批处理文件运行所有实验 *Batch file runs all experiments*
- [ ] 在Strawberry\目录中生成输出文件 *Output files generated in Strawberry\ directory*
- [ ] 结果显示开花天数、收获重量等 *Results show flowering days, harvest weights, etc.*

## 🪟 Windows特定提示 (Windows-Specific Tips)

1. **优先使用PowerShell而非命令提示符** (Use PowerShell over Command Prompt):
   - PowerShell对现代命令有更好的支持 *PowerShell has better support for modern commands*
   - 更好地处理带空格的路径 *Handles paths with spaces better*
   - 与Docker语法更一致 *More consistent with Docker syntax*

2. **文件路径助手** (File path helpers):
   - 使用Tab键自动完成 *Use Tab for autocomplete*
   - 将文件夹拖入终端以获取完整路径 *Drag folder into terminal to get full path*
   - 在PowerShell中使用 `~` 表示主目录 *Use `~` for home directory in PowerShell*

3. **Docker资源设置** (Docker resource settings):
   - Docker Desktop → 设置 → 资源 *Docker Desktop → Settings → Resources*
   - 如果构建慢，分配更多CPU/内存 *Allocate more CPU/memory if builds are slow*
   - 启用WSL 2集成以获得更好性能 *Enable WSL 2 integration for better performance*

4. **Windows终端 (推荐)** (Windows Terminal - Recommended):
   - 从Microsoft Store安装 *Install from Microsoft Store*
   - 比默认命令提示符更好的界面 *Better interface than default Command Prompt*
   - 支持多种shell类型 *Supports multiple shell types*

## 🎓 下一步 (Next Steps)

现在您已经在Windows上使用Docker运行DSSAT，可以:
*Now that you have DSSAT running with Docker on Windows, you can:*

1. **修改实验**: 编辑.SRX文件测试不同条件 *Modify experiments: Edit .SRX files to test different conditions*
2. **创建自定义批处理文件**: 组合不同实验 *Create custom batch files: Combine different experiments*
3. **分析输出**: 使用.OUT文件进行研究 *Analyze outputs: Use the .OUT files for your research*
4. **扩大规模**: 高效运行多个场景 *Scale up: Run multiple scenarios efficiently*
5. **分享结果**: Docker确保跨系统的可重现结果 *Share results: Docker ensures reproducible results across systems*

## 📧 支持 (Support)

如果您在Windows上遇到问题:
*If you encounter issues on Windows:*
1. 检查上面的故障排除部分 *Check the troubleshooting section above*
2. 验证Docker Desktop是否正常运行 *Verify Docker Desktop is running properly*
3. 尝试使用PowerShell而非命令提示符 *Try PowerShell instead of Command Prompt*
4. 确保在需要时有管理员权限 *Ensure you have administrator privileges when needed*
5. 如果Docker有网络问题，检查Windows防火墙设置 *Check Windows firewall settings if Docker has network issues*

## 🔄 PowerShell vs 命令提示符快速参考 (PowerShell vs Command Prompt Quick Reference)

| 任务 (Task) | PowerShell | 命令提示符 (Command Prompt) |
|-------------|------------|----------------------------|
| 当前目录 (Current directory) | `${PWD}` | `%cd%` |
| 复制文件 (Copy files) | `Copy-Item -Recurse` | `xcopy /E` |
| 列出文件 (List files) | `Get-ChildItem` | `dir` |
| 查看文件 (View file) | `Get-Content` | `type` |
| 计算行数 (Count lines) | `Measure-Object -Line` | `find /C /V ""` |

---

**恭喜！您现在拥有一个完全功能的DSSAT Docker设置，可以在Windows上进行草莓仿真！🍓🪟**
*Congratulations! You now have a fully functional DSSAT Docker setup for strawberry simulations on Windows! 🍓🪟* 