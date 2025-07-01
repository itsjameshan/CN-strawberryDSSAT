# DSSAT-CROPGRO Strawberry Model - Complete Docker Environment
# 集成Python环境和DSSAT构建的完整Docker解决方案
# 复制此文件的全部内容，保存为 Dockerfile（无扩展名）

FROM ubuntu:22.04

# 设置非交互式安装，避免tzdata等包的交互提示
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# 设置工作目录
WORKDIR /app

# 安装系统依赖（包括构建工具、Python、CMake、Fortran编译器等）
RUN apt-get update && apt-get install -y \
    # 基础系统工具
    wget \
    curl \
    git \
    unzip \
    build-essential \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release \
    # Python相关
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    # DSSAT构建依赖
    cmake \
    gfortran \
    make \
    # 其他可能需要的包
    liblapack-dev \
    libblas-dev \
    libatlas-base-dev \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建Python符号链接（确保python命令可用）
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# 设置pip使用中国镜像源（避免网络问题）
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = https://pypi.tuna.tsinghua.edu.cn/simple/' >> ~/.pip/pip.conf && \
    echo 'extra-index-url = https://mirrors.aliyun.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = pypi.tuna.tsinghua.edu.cn' >> ~/.pip/pip.conf && \
    echo '              mirrors.aliyun.com' >> ~/.pip/pip.conf && \
    echo 'timeout = 300' >> ~/.pip/pip.conf

# 升级pip到最新版本
RUN python -m pip install --upgrade pip

# 创建虚拟环境
RUN python -m venv /app/venv

# 激活虚拟环境并安装Python包
RUN /app/venv/bin/pip install --no-cache-dir \
    numpy>=1.19.0 \
    pandas>=1.3.0 \
    matplotlib>=3.3.0 \
    scipy>=1.7.0 \
    numba>=0.56.0 \
    openpyxl>=3.0.0 \
    xlrd>=2.0.0 \
    jupyter \
    ipython

# 设置环境变量以使用虚拟环境
ENV PATH="/app/venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/venv"

# 创建DSSAT目录结构
RUN mkdir -p /app/dssat /app/dssat-build /app/data

# 复制DSSAT源代码和数据文件（这些将在运行时挂载）
# 设置DSSAT环境变量
ENV DSSAT_DIR=/app/dssat
ENV PATH="$DSSAT_DIR:$PATH"

# 创建构建脚本
RUN echo '#!/bin/bash' > /app/build_dssat.sh && \
    echo 'set -e' >> /app/build_dssat.sh && \
    echo 'echo "Building DSSAT-CSM..."' >> /app/build_dssat.sh && \
    echo 'cd /app/dssat-build' >> /app/build_dssat.sh && \
    echo 'if [ -d "/app/dssat-source" ]; then' >> /app/build_dssat.sh && \
    echo '  echo "Configuring DSSAT with CMake..."' >> /app/build_dssat.sh && \
    echo '  cmake /app/dssat-source \' >> /app/build_dssat.sh && \
    echo '    -DCMAKE_INSTALL_PREFIX=/app/dssat \' >> /app/build_dssat.sh && \
    echo '    -DCMAKE_Fortran_FLAGS="-fallow-argument-mismatch -std=legacy -w -fno-range-check -ffixed-form -ffixed-line-length-none" \' >> /app/build_dssat.sh && \
    echo '    -DCMAKE_BUILD_TYPE=Release' >> /app/build_dssat.sh && \
    echo '  echo "Compiling DSSAT..."' >> /app/build_dssat.sh && \
    echo '  make -j$(nproc)' >> /app/build_dssat.sh && \
    echo '  echo "Installing DSSAT..."' >> /app/build_dssat.sh && \
    echo '  make install' >> /app/build_dssat.sh && \
    echo '  echo "DSSAT build completed successfully!"' >> /app/build_dssat.sh && \
    echo 'else' >> /app/build_dssat.sh && \
    echo '  echo "Warning: DSSAT source not found. Skipping DSSAT build."' >> /app/build_dssat.sh && \
    echo '  echo "DSSAT functionality will not be available."' >> /app/build_dssat.sh && \
    echo 'fi' >> /app/build_dssat.sh && \
    chmod +x /app/build_dssat.sh

# 创建运行脚本
RUN echo '#!/bin/bash' > /app/run_dssat.sh && \
    echo 'set -e' >> /app/run_dssat.sh && \
    echo 'echo "DSSAT-CROPGRO Strawberry Model Runner"' >> /app/run_dssat.sh && \
    echo 'echo "====================================="' >> /app/run_dssat.sh && \
    echo '' >> /app/run_dssat.sh && \
    echo '# 激活Python虚拟环境' >> /app/run_dssat.sh && \
    echo 'source /app/venv/bin/activate' >> /app/run_dssat.sh && \
    echo '' >> /app/run_dssat.sh && \
    echo '# 检查DSSAT是否已构建' >> /app/run_dssat.sh && \
    echo 'if [ ! -f "/app/dssat/dscsm048" ]; then' >> /app/run_dssat.sh && \
    echo '  echo "DSSAT not found. Building DSSAT..."' >> /app/run_dssat.sh && \
    echo '  /app/build_dssat.sh' >> /app/run_dssat.sh && \
    echo 'fi' >> /app/run_dssat.sh && \
    echo '' >> /app/run_dssat.sh && \
    echo '# 设置Python路径' >> /app/run_dssat.sh && \
    echo 'export PYTHONPATH="/app/data:$PYTHONPATH"' >> /app/run_dssat.sh && \
    echo '' >> /app/run_dssat.sh && \
    echo '# 检查参数' >> /app/run_dssat.sh && \
    echo 'if [ "$#" -eq 0 ]; then' >> /app/run_dssat.sh && \
    echo '  echo "Usage:"' >> /app/run_dssat.sh && \
    echo '  echo "  $0 python <script.py>     # Run Python script"' >> /app/run_dssat.sh && \
    echo '  echo "  $0 dssat <command>        # Run DSSAT command"' >> /app/run_dssat.sh && \
    echo '  echo "  $0 test                   # Run all tests"' >> /app/run_dssat.sh && \
    echo '  echo "  $0 bash                   # Start interactive bash"' >> /app/run_dssat.sh && \
    echo '  exit 1' >> /app/run_dssat.sh && \
    echo 'fi' >> /app/run_dssat.sh && \
    echo '' >> /app/run_dssat.sh && \
    echo 'cd /app/data' >> /app/run_dssat.sh && \
    echo '' >> /app/run_dssat.sh && \
    echo 'case "$1" in' >> /app/run_dssat.sh && \
    echo '  "python")' >> /app/run_dssat.sh && \
    echo '    shift' >> /app/run_dssat.sh && \
    echo '    echo "Running Python script: $@"' >> /app/run_dssat.sh && \
    echo '    python "$@"' >> /app/run_dssat.sh && \
    echo '    ;;' >> /app/run_dssat.sh && \
    echo '  "dssat")' >> /app/run_dssat.sh && \
    echo '    shift' >> /app/run_dssat.sh && \
    echo '    echo "Running DSSAT command: $@"' >> /app/run_dssat.sh && \
    echo '    /app/dssat/dscsm048 "$@"' >> /app/run_dssat.sh && \
    echo '    ;;' >> /app/run_dssat.sh && \
    echo '  "test")' >> /app/run_dssat.sh && \
    echo '    echo "Running all tests..."' >> /app/run_dssat.sh && \
    echo '    # 测试Python环境' >> /app/run_dssat.sh && \
    echo '    echo "Testing Python packages..."' >> /app/run_dssat.sh && \
    echo '    python -c "import numpy, pandas, matplotlib, scipy, numba, openpyxl; print(\"All Python packages imported successfully!\")"' >> /app/run_dssat.sh && \
    echo '    # 运行测试脚本（如果存在）' >> /app/run_dssat.sh && \
    echo '    if [ -f "cropgro-strawberry-test1.py" ]; then' >> /app/run_dssat.sh && \
    echo '      echo "Running cropgro-strawberry-test1.py..."' >> /app/run_dssat.sh && \
    echo '      python cropgro-strawberry-test1.py' >> /app/run_dssat.sh && \
    echo '    fi' >> /app/run_dssat.sh && \
    echo '    # 测试DSSAT（如果可用）' >> /app/run_dssat.sh && \
    echo '    if [ -f "/app/dssat/dscsm048" ]; then' >> /app/run_dssat.sh && \
    echo '      echo "DSSAT is available at: /app/dssat/dscsm048"' >> /app/run_dssat.sh && \
    echo '    else' >> /app/run_dssat.sh && \
    echo '      echo "DSSAT not available. Python-only mode."' >> /app/run_dssat.sh && \
    echo '    fi' >> /app/run_dssat.sh && \
    echo '    ;;' >> /app/run_dssat.sh && \
    echo '  "bash")' >> /app/run_dssat.sh && \
    echo '    echo "Starting interactive bash session..."' >> /app/run_dssat.sh && \
    echo '    echo "Virtual environment activated. DSSAT available at /app/dssat/"' >> /app/run_dssat.sh && \
    echo '    exec bash' >> /app/run_dssat.sh && \
    echo '    ;;' >> /app/run_dssat.sh && \
    echo '  *)' >> /app/run_dssat.sh && \
    echo '    echo "Unknown command: $1"' >> /app/run_dssat.sh && \
    echo '    echo "Use: python, dssat, test, or bash"' >> /app/run_dssat.sh && \
    echo '    exit 1' >> /app/run_dssat.sh && \
    echo '    ;;' >> /app/run_dssat.sh && \
    echo 'esac' >> /app/run_dssat.sh && \
    chmod +x /app/run_dssat.sh

# 创建Python环境测试脚本
RUN echo '#!/usr/bin/env python3' > /app/test_environment.py && \
    echo '"""Test script to verify the Python environment setup"""' >> /app/test_environment.py && \
    echo '' >> /app/test_environment.py && \
    echo 'import sys' >> /app/test_environment.py && \
    echo 'import os' >> /app/test_environment.py && \
    echo '' >> /app/test_environment.py && \
    echo 'def test_python_packages():' >> /app/test_environment.py && \
    echo '    """Test if all required Python packages can be imported"""' >> /app/test_environment.py && \
    echo '    packages = {' >> /app/test_environment.py && \
    echo '        "numpy": "numpy",' >> /app/test_environment.py && \
    echo '        "pandas": "pandas",' >> /app/test_environment.py && \
    echo '        "matplotlib": "matplotlib",' >> /app/test_environment.py && \
    echo '        "scipy": "scipy",' >> /app/test_environment.py && \
    echo '        "numba": "numba",' >> /app/test_environment.py && \
    echo '        "openpyxl": "openpyxl"' >> /app/test_environment.py && \
    echo '    }' >> /app/test_environment.py && \
    echo '    ' >> /app/test_environment.py && \
    echo '    print("Testing Python package imports...")' >> /app/test_environment.py && \
    echo '    for name, module in packages.items():' >> /app/test_environment.py && \
    echo '        try:' >> /app/test_environment.py && \
    echo '            __import__(module)' >> /app/test_environment.py && \
    echo '            print(f"✓ {name} imported successfully")' >> /app/test_environment.py && \
    echo '        except ImportError as e:' >> /app/test_environment.py && \
    echo '            print(f"✗ Failed to import {name}: {e}")' >> /app/test_environment.py && \
    echo '            return False' >> /app/test_environment.py && \
    echo '    return True' >> /app/test_environment.py && \
    echo '' >> /app/test_environment.py && \
    echo 'def test_dssat_availability():' >> /app/test_environment.py && \
    echo '    """Test if DSSAT is available"""' >> /app/test_environment.py && \
    echo '    dssat_path = "/app/dssat/dscsm048"' >> /app/test_environment.py && \
    echo '    if os.path.isfile(dssat_path):' >> /app/test_environment.py && \
    echo '        print(f"✓ DSSAT found at: {dssat_path}")' >> /app/test_environment.py && \
    echo '        return True' >> /app/test_environment.py && \
    echo '    else:' >> /app/test_environment.py && \
    echo '        print(f"✗ DSSAT not found at: {dssat_path}")' >> /app/test_environment.py && \
    echo '        return False' >> /app/test_environment.py && \
    echo '' >> /app/test_environment.py && \
    echo 'if __name__ == "__main__":' >> /app/test_environment.py && \
    echo '    print("=" * 50)' >> /app/test_environment.py && \
    echo '    print("DSSAT-CROPGRO Environment Test")' >> /app/test_environment.py && \
    echo '    print("=" * 50)' >> /app/test_environment.py && \
    echo '    print(f"Python version: {sys.version}")' >> /app/test_environment.py && \
    echo '    print(f"Virtual environment: {os.environ.get(\"VIRTUAL_ENV\", \"Not detected\")}")' >> /app/test_environment.py && \
    echo '    print()' >> /app/test_environment.py && \
    echo '    ' >> /app/test_environment.py && \
    echo '    success = True' >> /app/test_environment.py && \
    echo '    success &= test_python_packages()' >> /app/test_environment.py && \
    echo '    success &= test_dssat_availability()' >> /app/test_environment.py && \
    echo '    ' >> /app/test_environment.py && \
    echo '    print()' >> /app/test_environment.py && \
    echo '    if success:' >> /app/test_environment.py && \
    echo '        print("✓ All tests passed! Environment is ready.")' >> /app/test_environment.py && \
    echo '        exit(0)' >> /app/test_environment.py && \
    echo '    else:' >> /app/test_environment.py && \
    echo '        print("✗ Some tests failed. Check the errors above.")' >> /app/test_environment.py && \
    echo '        exit(1)' >> /app/test_environment.py && \
    chmod +x /app/test_environment.py

# Create run_dssat utility script during build
RUN echo '#!/bin/bash' > /app/run_dssat && \
    echo '# DSSAT runner utility script' >> /app/run_dssat && \
    echo '# Built into Docker image for reliable access' >> /app/run_dssat && \
    echo '' >> /app/run_dssat && \
    echo 'DSSAT_EXECUTABLE="/app/dssat/dscsm048"' >> /app/run_dssat && \
    echo '' >> /app/run_dssat && \
    echo 'if [ ! -f "$DSSAT_EXECUTABLE" ]; then' >> /app/run_dssat && \
    echo '    echo "Error: DSSAT executable not found at $DSSAT_EXECUTABLE"' >> /app/run_dssat && \
    echo '    exit 1' >> /app/run_dssat && \
    echo 'fi' >> /app/run_dssat && \
    echo '' >> /app/run_dssat && \
    echo 'exec "$DSSAT_EXECUTABLE" "$@"' >> /app/run_dssat && \
    chmod +x /app/run_dssat

# Add /app to PATH so run_dssat is accessible
ENV PATH="/app:$PATH"

# 设置入口点
ENTRYPOINT ["/app/run_dssat.sh"]
CMD ["test"]

# 暴露端口（如果需要运行Jupyter等）
EXPOSE 8888

# 添加标签
LABEL maintainer="DSSAT-CROPGRO-Strawberry" \
      description="Complete Docker environment for DSSAT-CROPGRO strawberry modeling with Python integration" \
      version="1.0"