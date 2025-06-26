#!/usr/bin/env bash

# 快速修复 python3-pip 问题 / Quick Fix for python3-pip Issues
# 解决 "E: Package 'python3-pip' has no installation candidate"

echo "=== 快速修复 python3-pip 问题 ==="
echo "=== Quick Fix for python3-pip Issues ==="
echo ""

# 检查系统
if ! command -v apt-get >/dev/null 2>&1; then
    echo "❌ 此脚本仅适用于 Ubuntu/Debian 系统"
    echo "❌ This script is only for Ubuntu/Debian systems"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 未安装，请先安装 python3"
    echo "❌ python3 not installed, please install python3 first"
    exit 1
fi

echo "✅ 系统检查通过"
echo "✅ System check passed"
echo ""

# 方法1: 更新软件包列表
echo "方法1: 更新软件包列表..."
echo "Method 1: Updating package lists..."

sudo apt-get update

if sudo apt-get install -y python3-pip; then
    echo "✅ python3-pip 安装成功！"
    echo "✅ python3-pip installed successfully!"
    pip3 --version
    exit 0
else
    echo "❌ 方法1失败，尝试方法2..."
    echo "❌ Method 1 failed, trying method 2..."
fi

echo ""

# 方法2: 配置阿里云镜像源
echo "方法2: 配置阿里云镜像源..."
echo "Method 2: Configuring Alibaba Cloud mirror..."

# 备份原始源列表
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)

# 检测系统版本
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    OS_NAME="$ID"
    OS_VERSION="$VERSION_ID"
    echo "检测到系统: $OS_NAME $OS_VERSION"
    echo "Detected system: $OS_NAME $OS_VERSION"
else
    echo "❌ 无法检测系统版本"
    echo "❌ Cannot detect system version"
    exit 1
fi

# 配置镜像源
case "$OS_NAME" in
    "ubuntu")
        MIRROR_URL="https://mirrors.aliyun.com/ubuntu/"
        ;;
    "debian")
        MIRROR_URL="https://mirrors.aliyun.com/debian/"
        ;;
    *)
        echo "❌ 不支持的系统: $OS_NAME"
        echo "❌ Unsupported system: $OS_NAME"
        exit 1
        ;;
esac

echo "配置镜像源: $MIRROR_URL"
echo "Configuring mirror: $MIRROR_URL"

sudo tee /etc/apt/sources.list > /dev/null << EOF
# Updated by quick fix script
deb $MIRROR_URL $OS_VERSION main restricted universe multiverse
deb $MIRROR_URL $OS_VERSION-updates main restricted universe multiverse
deb $MIRROR_URL $OS_VERSION-security main restricted universe multiverse
EOF

# 更新软件包列表
sudo apt-get update

if sudo apt-get install -y python3-pip; then
    echo "✅ python3-pip 安装成功！"
    echo "✅ python3-pip installed successfully!"
    pip3 --version
    exit 0
else
    echo "❌ 方法2失败，尝试方法3..."
    echo "❌ Method 2 failed, trying method 3..."
fi

echo ""

# 方法3: 使用 get-pip.py
echo "方法3: 使用 get-pip.py..."
echo "Method 3: Using get-pip.py..."

if command -v curl >/dev/null 2>&1; then
    DOWNLOAD_CMD="curl -L"
elif command -v wget >/dev/null 2>&1; then
    DOWNLOAD_CMD="wget -O -"
else
    echo "❌ 未找到 curl 或 wget"
    echo "❌ Neither curl nor wget found"
    exit 1
fi

echo "下载 get-pip.py..."
echo "Downloading get-pip.py..."

if $DOWNLOAD_CMD https://bootstrap.pypa.io/get-pip.py > get-pip.py 2>/dev/null; then
    echo "✅ 下载成功"
    echo "✅ Download successful"
    
    if python3 get-pip.py --user; then
        echo "✅ pip 安装成功！"
        echo "✅ pip installed successfully!"
        
        # 添加到PATH
        export PATH="$HOME/.local/bin:$PATH"
        
        # 清理
        rm -f get-pip.py
        
        # 验证安装
        if ~/.local/bin/pip3 --version >/dev/null 2>&1; then
            echo "✅ pip 验证成功"
            echo "✅ pip verification successful"
            ~/.local/bin/pip3 --version
            exit 0
        fi
    else
        echo "❌ pip 安装失败"
        echo "❌ pip installation failed"
        rm -f get-pip.py
    fi
else
    echo "❌ 下载 get-pip.py 失败"
    echo "❌ Failed to download get-pip.py"
fi

echo ""
echo "❌ 所有方法都失败了"
echo "❌ All methods failed"
echo ""
echo "请尝试手动安装:"
echo "Please try manual installation:"
echo "1. sudo apt-get update && sudo apt-get install python3-pip"
echo "2. curl -L https://bootstrap.pypa.io/get-pip.py | python3"
echo "3. 检查网络连接和系统配置"
echo "3. Check network connectivity and system configuration" 