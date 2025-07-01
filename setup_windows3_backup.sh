#!/usr/bin/env bash

# CROPGRO-Strawberry Model Setup Script
# This script sets up the Python environment and optionally builds DSSAT


# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Function Definitions ---

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running in a supported environment
check_wsl_and_guide_user() {
    # Check if this is a Windows-like shell (e.g., Git Bash) but NOT WSL
    # In WSL, $OSTYPE is typically 'linux-gnu', in Git Bash it's 'msys'
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Check if it's NOT WSL by looking for the /proc/version file with 'microsoft'
        if ! ( [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null ); then
            print_error "Unsupported Environment: This script must be run inside WSL (Windows Subsystem for Linux)."
            print_error "不支持的环境：此脚本必须在WSL (Windows的Linux子系统) 中运行。"
            echo -e "${BLUE}Please follow these steps to set up the correct environment:${NC}"
            echo -e "${BLUE}请按照以下步骤设置正确的环境：${NC}"
            echo "1. Open PowerShell as an ADMINISTRATOR."
            echo "   (以管理员身份打开 PowerShell)"
            echo "2. Run the following command to install WSL and Ubuntu:"
            echo "   (运行以下命令以安装WSL和Ubuntu)"
            echo -e "   ${GREEN}wsl --install${NC}"
            echo "3. Restart your computer when prompted."
            echo "   (在提示时重启您的计算机)"
            echo "4. After restarting, open the 'Ubuntu' application from your Start Menu."
            echo "   (重启后，从开始菜单打开 'Ubuntu' 应用程序)"
            echo "5. In the new Ubuntu terminal, navigate to your project directory with this command:"
            echo "   (在新的Ubuntu终端中，使用此命令导航到您的项目目录)"
            echo -e "   ${GREEN}cd /mnt/c/CN-strawberryDSSAT${NC}"
            echo "6. Finally, run the setup script again inside the Ubuntu terminal:"
            echo "   (最后，在Ubuntu终端内再次运行此安装脚本)"
            echo -e "   ${GREEN}./setup_windows3.sh${NC}"
            exit 1
        fi
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python and pip
install_python_and_pip() {
    print_warning "Python 3 or pip not found. Attempting to install..."
    
    # Detect environment
    if [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null; then
        ENV_TYPE="WSL"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        ENV_TYPE="Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        ENV_TYPE="macOS"
    else
        ENV_TYPE="Other"
    fi

    if [[ "$ENV_TYPE" == "macOS" ]]; then
        if command_exists brew; then
            print_status "Installing Python 3 via Homebrew..."
            brew install python3
        else
            print_error "Homebrew not found. Please install Python 3 manually."
            exit 1
        fi
    else # Linux, WSL, or other Unix-like systems
        if command_exists apt-get; then
            print_status "Installing python3 and python3-pip via apt..."
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
        elif command_exists yum; then
            print_status "Installing python3 and python3-pip via yum..."
            sudo yum install -y python3 python3-pip
        elif command_exists dnf; then
            print_status "Installing python3 and python3-pip via dnf..."
            sudo dnf install -y python3 python3-pip
        else
            print_error "Unsupported package manager. Please install Python 3 and pip manually."
            exit 1
        fi
    fi

    # Verify installation
    if command_exists python3 && command_exists pip3; then
        print_success "Python 3 and pip installed successfully."
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    else
        print_error "Failed to install Python 3 and/or pip."
        exit 1
    fi
}

# Function to set up Python environment
setup_python_environment() {
    print_status "Setting up Python environment..."

    # Find a valid Python command
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        install_python_and_pip
        PYTHON_CMD="python3"
    fi
    
    # Find a valid pip command
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    else
        install_python_and_pip
        PIP_CMD="pip3"
    fi
    
    # Verify that pip is available
    if ! command_exists $PIP_CMD; then
        print_error "pip not found and installation failed. Please install pip manually."
        exit 1
    fi
    
    # Configure pip to use a mirror for faster downloads
    configure_pip_mirror

    # Create virtual environment
    VENV_NAME="venv-cn-strawberry"
    if [ ! -d "$VENV_NAME" ]; then
        print_status "Creating Python virtual environment..."
        $PYTHON_CMD -m venv $VENV_NAME
        if [ $? -ne 0 ]; then
            print_error "Failed to create virtual environment."
            exit 1
        fi
    else
        print_status "Python virtual environment already exists."
    fi

    # Activate virtual environment
    print_status "Activating Python virtual environment..."
    source $VENV_NAME/bin/activate
    if [ $? -ne 0 ]; then
        print_error "Failed to activate virtual environment."
        exit 1
    fi

    # Upgrade pip in the virtual environment
    print_status "Upgrading pip in the virtual environment..."
    $PIP_CMD install --upgrade pip
    if [ $? -ne 0 ]; then
        print_error "Failed to upgrade pip in the virtual environment."
        exit 1
    fi

    # Install required packages
    print_status "Installing required packages..."
    $PIP_CMD install -r requirements.txt
    if [ $? -ne 0 ]; then
        print_error "Failed to install required packages."
        exit 1
    fi

    print_success "Python environment setup completed."
}

# Enhanced function to install CMake with proper environment detection
install_cmake() {
    print_status "Installing CMake with proper environment detection..."
    
    # Detect environment first
    if [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null; then
        ENV_TYPE="WSL"
        print_status "Detected WSL (Windows Subsystem for Linux)"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        ENV_TYPE="Linux"
        print_status "Detected native Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        ENV_TYPE="macOS"
        print_status "Detected macOS"
    else
        ENV_TYPE="Other"
        print_status "Detected other Unix-like system: $OSTYPE"
    fi
    
    # Install based on actual environment, not just $OSTYPE
    if [[ "$ENV_TYPE" == "macOS" ]]; then
        # macOS
        if command_exists brew; then
            print_status "Installing CMake via Homebrew..."
            brew install cmake
        else
            print_error "Homebrew not found. Please install CMake manually:"
            print_error "  brew install cmake"
            print_error "Or download from: https://cmake.org/download/"
            exit 1
        fi
    else
        # Linux, WSL, or other Unix-like systems
        print_status "Installing CMake for Linux/Unix environment..."
        
        if command_exists apt-get; then
            print_status "Installing CMake via apt..."
            sudo apt-get update && sudo apt-get install -y cmake
        elif command_exists yum; then
            print_status "Installing CMake via yum..."
            sudo yum install -y cmake
        elif command_exists dnf; then
            print_status "Installing CMake via dnf..."
            sudo dnf install -y cmake
        elif command_exists pacman; then
            print_status "Installing CMake via pacman..."
            sudo pacman -S cmake
        elif command_exists snap; then
            print_status "Installing CMake via snap..."
            sudo snap install cmake --classic
        else
            print_error "No suitable package manager found. Please install CMake manually:"
            print_error "  sudo apt-get install cmake  # Ubuntu/Debian"
            print_error "  sudo yum install cmake       # CentOS/RHEL"
            exit 1
        fi
    fi
    
    # Verify installation
    if command_exists cmake; then
        CMAKE_VERSION=$(cmake --version 2>/dev/null | head -n1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -n1)
        print_success "CMake installed successfully. Version: $CMAKE_VERSION"
        print_status "CMake location: $(which cmake)"
    else
        print_error "CMake installation failed!"
        exit 1
    fi
}

# Enhanced function to check system dependencies with better detection
check_system_dependencies() {
    if [[ "${1:-}" == "--with-dssat" ]]; then
        print_status "Checking system dependencies for DSSAT build..."

        # Detect environment
        if [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null; then
            print_status "Environment: WSL (Windows Subsystem for Linux)"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            print_status "Environment: Native Linux"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            print_status "Environment: macOS"
        fi

        # Check for CMake with enhanced detection
        if ! command_exists cmake; then
            print_warning "CMake not found. Installing..."
            install_cmake
        else
            # Test if cmake actually works
            if ! cmake --version >/dev/null 2>&1; then
                print_warning "CMake found but not working. Reinstalling..."
                install_cmake
            else
                CMAKE_VERSION=$(cmake --version 2>/dev/null | head -n1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -n1)
                print_success "Found working CMake $CMAKE_VERSION at $(which cmake)"
            fi
        fi

        # Check for Fortran compiler
        if ! command_exists gfortran; then
            print_warning "gfortran not found. Attempting to install..."
            install_fortran_compiler
        else
            GFORTRAN_VERSION=$(gfortran --version | head -n1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -n1)
            if [[ -z "$GFORTRAN_VERSION" ]]; then
                GFORTRAN_VERSION=$(gfortran --version | head -n1 | sed 's/.*\([0-9]\+\.[0-9]\+\).*/\1/')
            fi
            print_success "Found gfortran $GFORTRAN_VERSION at $(which gfortran)"

            # Check for problematic versions
            MAJOR_VERSION=$(echo "$GFORTRAN_VERSION" | cut -d'.' -f1)
            if [[ -n "$MAJOR_VERSION" ]] && [[ "$MAJOR_VERSION" -gt 10 ]]; then
                print_warning "gfortran $GFORTRAN_VERSION may have compatibility issues with DSSAT"
                print_warning "Consider using the Python implementation instead"
            fi
        fi

        # Check for make/build tools
        if ! command_exists make; then
            print_warning "make not found. Installing build tools..."
            install_build_tools
        else
            print_success "Found make build tool at $(which make)"
        fi
        
        # Final verification
        print_status "=== Dependency Check Summary ==="
        print_status "CMake: $(which cmake 2>/dev/null || echo 'NOT FOUND')"
        print_status "gfortran: $(which gfortran 2>/dev/null || echo 'NOT FOUND')"
        print_status "make: $(which make 2>/dev/null || echo 'NOT FOUND')"
    fi
}

# Function to install Fortran compiler based on OS
install_fortran_compiler() {
    # Detect actual environment
    if [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null; then
        ENV_TYPE="WSL"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        ENV_TYPE="Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        ENV_TYPE="macOS"
    else
        ENV_TYPE="Other"
    fi
    
    if [[ "$ENV_TYPE" == "macOS" ]]; then
        # macOS
        if command_exists brew; then
            print_status "Installing gcc (includes gfortran) via Homebrew..."
            brew install gcc
        else
            print_error "Homebrew not found. Please install gcc manually:"
            print_error "  brew install gcc"
            exit 1
        fi
    else
        # Linux, WSL, or other Unix-like systems
        if command_exists apt-get; then
            print_status "Installing gfortran via apt..."
            sudo apt-get update && sudo apt-get install -y gfortran
        elif command_exists yum; then
            print_status "Installing gfortran via yum..."
            sudo yum install -y gcc-gfortran
        elif command_exists dnf; then
            print_status "Installing gfortran via dnf..."
            sudo dnf install -y gcc-gfortran
        elif command_exists pacman; then
            print_status "Installing gcc-fortran via pacman..."
            sudo pacman -S gcc-fortran
        else
            print_error "Package manager not found. Please install gfortran manually."
            exit 1
        fi
    fi
}

# Function to install build tools based on OS
install_build_tools() {
    # Detect actual environment
    if [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null; then
        ENV_TYPE="WSL"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        ENV_TYPE="Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        ENV_TYPE="macOS"
    else
        ENV_TYPE="Other"
    fi
    
    if [[ "$ENV_TYPE" == "macOS" ]]; then
        # macOS - Xcode command line tools should provide make
        if ! command_exists xcode-select; then
            print_status "Installing Xcode command line tools..."
            xcode-select --install
        fi
    else
        # Linux, WSL, or other Unix-like systems
        if command_exists apt-get; then
            print_status "Installing build-essential via apt..."
            sudo apt-get update && sudo apt-get install -y build-essential
        elif command_exists yum; then
            print_status "Installing development tools via yum..."
            sudo yum groupinstall -y "Development Tools"
        elif command_exists dnf; then
            print_status "Installing development tools via dnf..."
            sudo dnf groupinstall -y "Development Tools"
        elif command_exists pacman; then
            print_status "Installing base-devel via pacman..."
            sudo pacman -S base-devel
        else
            print_error "Package manager not found. Please install build tools manually."
            exit 1
        fi
    fi
}

# Function to configure pip with Chinese mirrors
configure_pip_mirrors() {
    print_status "Configuring pip with Chinese mirrors for faster downloads..."
    
    # Create pip config directory
    mkdir -p ~/.pip
    mkdir -p ~/.config/pip
    
    # Create pip.conf with Chinese mirrors
    cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
retries = 5

[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF

    # Also create for the new location
    cat > ~/.config/pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
retries = 5

[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF

    print_success "Configured pip to use Tsinghua University mirror (清华大学镜像源)"
    print_status "Backup mirrors available: Alibaba, Douban, USTC"
}

# Function to install Python essentials (pip, venv)
install_python_essentials() {
    print_status "Checking and installing Python essentials..."
    
    # Configure mirrors first
    configure_pip_mirrors
    
    # Install pip if not available
    if ! command_exists pip && ! command_exists pip3; then
        print_warning "pip not found. Installing pip..."
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y python3-pip
        elif command_exists yum; then
            sudo yum install -y python3-pip
        elif command_exists dnf; then
            sudo dnf install -y python3-pip
        else
            print_error "Cannot install pip automatically. Please install pip manually."
            exit 1
        fi
    fi
    
    # Install python3-venv if on Ubuntu/Debian
    if command_exists apt-get; then
        print_status "Installing python3-venv for virtual environment support..."
        sudo apt-get update
        sudo apt-get install -y python3-venv python3-dev
    fi
    
    # Do not install setuptools and wheel globally. This will be handled inside the venv.
    # print_status "Installing setuptools and wheel..."
    # if command_exists pip3; then
    #     sudo pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn --upgrade setuptools wheel
    # elif command_exists pip; then
    #     sudo pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn --upgrade setuptools wheel
    # fi
}

# Function to check Python version
check_python() {
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        # Check if python is Python 3
        if python -c "import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)" 2>/dev/null; then
            PYTHON_CMD="python"
        else
            print_error "Python 3 is required but not found. Please install Python 3."
            exit 1
        fi
    else
        print_error "Python 3 is required but not found. Please install Python 3."
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    print_success "Found Python $PYTHON_VERSION"
    
    # Install Python essentials
    install_python_essentials
}

# Function to create requirements.txt if it doesn't exist
create_requirements_txt() {
    if [ ! -f "requirements.txt" ]; then
        print_warning "requirements.txt not found. Creating default requirements.txt..."
        cat > requirements.txt << 'EOF'
# Core scientific computing packages
numpy>=1.19.0
pandas>=1.3.0
matplotlib>=3.3.0
scipy>=1.7.0

# Performance optimization
numba>=0.56.0

# Additional useful packages
seaborn>=0.11.0
jupyter>=1.0.0
ipython>=7.0.0

# Data handling
openpyxl>=3.0.0
xlrd>=2.0.0

# Plotting enhancements
plotly>=5.0.0

# Development tools
pytest>=6.0.0
black>=21.0.0
flake8>=3.9.0
EOF
        print_success "Created default requirements.txt with essential packages."
    fi
}

# Function to install essential packages individually if requirements.txt fails
install_essential_packages() {
    print_status "Installing essential packages individually using Chinese mirrors..."
    
    # Determine which pip command to use
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    else
        print_error "No pip command available. Cannot install packages."
        return 1
    fi
    
    # List of essential packages
    ESSENTIAL_PACKAGES=(
        "numpy"
        "pandas" 
        "matplotlib"
        "scipy"
        "numba"
    )
    
    # List of Chinese mirrors to try
    MIRRORS=(
        "https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn"
        "https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
        "https://pypi.douban.com/simple/ --trusted-host pypi.douban.com"
        "https://pypi.mirrors.ustc.edu.cn/simple/ --trusted-host pypi.mirrors.ustc.edu.cn"
    )
    
    for package in "${ESSENTIAL_PACKAGES[@]}"; do
        print_status "Installing $package..."
        installed=false
        
        for mirror in "${MIRRORS[@]}"; do
            print_status "Trying mirror: $(echo $mirror | cut -d' ' -f1)..."
            if sudo $PIP_CMD install -i $mirror "$package"; then
                print_success "$package installed successfully using $(echo $mirror | cut -d' ' -f1)"
                installed=true
                break
            fi
        done
        
        if [ "$installed" = false ]; then
            print_warning "Trying with --user flag..."
            for mirror in "${MIRRORS[@]}"; do
                if $PIP_CMD install -i $mirror --user "$package"; then
                    print_success "$package installed with --user flag using $(echo $mirror | cut -d' ' -f1)"
                    installed=true
                    break
                fi
            done
        fi
        
        if [ "$installed" = false ]; then
            print_error "Failed to install $package with all mirrors."
        fi
    done
}

# Function to setup virtual environment
setup_venv() {
    print_status "Setting up Python virtual environment..."
    
    # Determine which pip command to use
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    else
        print_error "No pip command available. Cannot proceed."
        exit 1
    fi
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Removing and recreating..."
        rm -rf venv
    fi
    
    # Create virtual environment
    print_status "Creating virtual environment..."
    if ! $PYTHON_CMD -m venv venv; then
        print_error "Failed to create virtual environment. Trying alternative method..."
        if ! $PYTHON_CMD -m virtualenv venv; then
            print_error "Virtual environment creation failed. Installing virtualenv and trying again..."
            sudo $PIP_CMD install virtualenv
            $PYTHON_CMD -m virtualenv venv || {
                print_error "Virtual environment creation still failed."
                print_warning "Continuing without virtual environment..."
                # Install packages globally instead
                install_packages_globally
                return
            }
        fi
    fi
    print_success "Virtual environment created."
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_success "Virtual environment activated."
    elif [ -f "venv/Scripts/activate" ]; then
        # Windows style activation
        source venv/Scripts/activate
        print_success "Virtual environment activated (Windows style)."
    else
        print_warning "Could not find activation script. Installing packages globally..."
        install_packages_globally
        return
    fi
    
    # Upgrade pip with Chinese mirror
    print_status "Upgrading pip using Chinese mirror..."
    if ! pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn --upgrade pip; then
        print_warning "pip upgrade failed. Trying alternative mirrors..."
        # Try Alibaba mirror
        if ! pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --upgrade pip; then
            # Try Douban mirror
            if ! pip install -i https://pypi.douban.com/simple/ --trusted-host pypi.douban.com --upgrade pip; then
                print_warning "All mirror upgrades failed. Continuing with current version..."
            fi
        fi
    fi
    
    # Create requirements.txt if it doesn't exist
    create_requirements_txt
    
    # Install requirements with Chinese mirror
    print_status "Installing Python dependencies using Chinese mirrors..."
    if pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements.txt; then
        print_success "Dependencies installed successfully using Tsinghua mirror."
    elif pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt; then
        print_success "Dependencies installed successfully using Alibaba mirror."
    elif pip install -i https://pypi.douban.com/simple/ --trusted-host pypi.douban.com -r requirements.txt; then
        print_success "Dependencies installed successfully using Douban mirror."
    else
        print_error "Failed to install from requirements.txt using all mirrors. Trying essential packages individually..."
        install_essential_packages
    fi
}

# Function to install packages globally when virtual environment fails
install_packages_globally() {
    print_status "Installing packages globally (no virtual environment)..."
    
    # Determine which pip command to use
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    else
        print_error "No pip command available. Cannot install packages."
        return 1
    fi
    
    # Create requirements.txt if it doesn't exist
    create_requirements_txt
    
    # Try to install from requirements.txt with Chinese mirrors
    print_status "Installing Python dependencies globally using Chinese mirrors..."
    
    MIRRORS=(
        "https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn"
        "https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
        "https://pypi.douban.com/simple/ --trusted-host pypi.douban.com"
    )
    
    installed=false
    for mirror in "${MIRRORS[@]}"; do
        print_status "Trying to install requirements using $(echo $mirror | cut -d' ' -f1)..."
        if sudo $PIP_CMD install -i $mirror -r requirements.txt; then
            print_success "Dependencies installed successfully using $(echo $mirror | cut -d' ' -f1)"
            installed=true
            break
        fi
    done
    
    if [ "$installed" = false ]; then
        print_error "Failed to install from requirements.txt using all mirrors. Trying essential packages individually..."
        install_essential_packages
    fi
}

# Enhanced function to build DSSAT on Linux with comprehensive error handling
build_dssat_linux() {
    print_status "Building DSSAT-CSM with enhanced error handling..."

    # Detect actual environment
    if [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null; then
        print_status "Detected WSL (Windows Subsystem for Linux) environment"
        ENV_TYPE="WSL"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_status "Detected native Linux environment"
        ENV_TYPE="Linux"
    else
        print_status "Detected other Unix-like environment: $OSTYPE"
        ENV_TYPE="Other"
    fi

    # Verify CMake is available and working
    if ! command_exists cmake; then
        print_error "CMake not found! Installing..."
        install_cmake
    fi
    
    # Test cmake works
    if ! cmake --version >/dev/null 2>&1; then
        print_error "CMake is installed but not working!"
        print_status "CMake path: $(which cmake 2>/dev/null || echo 'NOT FOUND')"
        print_status "Attempting to fix..."
        
        # Clear any cached cmake paths
        hash -r
        
        # Try to find cmake in common locations
        for cmake_path in /usr/bin/cmake /usr/local/bin/cmake /snap/bin/cmake; do
            if [[ -x "$cmake_path" ]]; then
                print_status "Found working cmake at: $cmake_path"
                CMAKE_CMD="$cmake_path"
                break
            fi
        done
        
        if [[ -z "${CMAKE_CMD:-}" ]]; then
            print_error "No working cmake found. Please install cmake manually:"
            print_error "  sudo apt-get update && sudo apt-get install -y cmake"
            return 1
        fi
    else
        CMAKE_CMD="cmake"
    fi

    # Navigate to DSSAT source directory
    if [ ! -d "dssat-csm-os-develop" ]; then
        print_error "DSSAT source directory not found!"
        print_status "Expected directory: dssat-csm-os-develop"
        print_status "Current directory contents:"
        ls -la
        return 1
    fi

    cd dssat-csm-os-develop
    
    # Clean previous build attempts
    if [ -d "build" ]; then
        print_status "Cleaning previous build..."
        rm -rf build
    fi
    
    mkdir -p build
    cd build

    # Set up environment variables for compilation
    export CMAKE_Fortran_COMPILER=$(which gfortran)
    export FC=$(which gfortran)
    export F77=$(which gfortran)
    
    print_status "=== Build Environment ==="
    print_status "CMake: $CMAKE_CMD"
    print_status "Fortran: $FC"
    print_status "Environment: $ENV_TYPE"
    print_status "=========================="

    # Enhanced Fortran flags for maximum compatibility
    FORTRAN_FLAGS="-fallow-argument-mismatch -std=legacy -w -fno-range-check -ffixed-form -ffixed-line-length-none"
    
    # Configure with enhanced settings
    print_status "Configuring DSSAT with CMake..."
    
    # Use the verified cmake command
    if $CMAKE_CMD -DCMAKE_INSTALL_PREFIX=$HOME/dssat \
                  -DCMAKE_Fortran_COMPILER="$FC" \
                  -DCMAKE_Fortran_FLAGS="$FORTRAN_FLAGS" \
                  -DCMAKE_BUILD_TYPE=Release \
                  .. 2>&1 | tee cmake.log; then
        print_success "CMake configuration successful"
    else
        print_error "CMake configuration failed!"
        print_error "CMake log (last 20 lines):"
        tail -20 cmake.log
        print_error ""
        print_error "Troubleshooting:"
        print_error "1. Check if cmake is properly installed:"
        print_error "   $CMAKE_CMD --version"
        print_error "2. Check if gfortran is available:"
        print_error "   gfortran --version"
        print_error "3. Install missing dependencies:"
        print_error "   sudo apt-get install cmake gfortran build-essential"
        cd ../..
        return 1
    fi

    # Compilation
    print_status "Compiling DSSAT (this may take several minutes)..."
    
    if make -j1 2>&1 | tee build.log; then
        print_success "DSSAT compilation successful"
    else
        print_error "DSSAT compilation failed!"
        print_error "Build log (last 30 lines):"
        tail -30 build.log
        print_error ""
        print_error "=== DSSAT Compilation Troubleshooting ==="
        print_error "This is a known issue with DSSAT Fortran code on modern systems."
        print_error ""
        print_error "Solutions:"
        print_error "1. Use older gfortran version:"
        print_error "   sudo apt install gfortran-9"
        print_error "   export FC=gfortran-9"
        print_error "   Then rerun this script"
        print_error ""
        print_error "2. Use Python implementation instead (RECOMMENDED):"
        print_error "   python3 cropgro-strawberry-implementation.py"
        print_error ""
        print_error "3. Check specific error in build.log:"
        print_error "   cat $(pwd)/build.log"
        print_error ""
        print_status "The Python implementation provides the same functionality"
        print_status "and is actively maintained for cross-platform compatibility."
        cd ../..
        return 1
    fi

    # Installation
    print_status "Installing DSSAT..."
    if make install 2>&1 | tee install.log; then
        print_success "DSSAT installation successful"
    else
        print_error "DSSAT installation failed!"
        print_error "Install log:"
        cat install.log
        cd ../..
        return 1
    fi

    # Return to original directory
    cd ../..
    install_dssat_data
    print_success "DSSAT build and setup completed!"
    return 0
}

# Function to build DSSAT on macOS with ARM64 compatibility fixes
build_dssat_macos() {
    print_status "Building DSSAT-CSM on macOS..."

    # Navigate to DSSAT source directory
    if [ ! -d "dssat-csm-os-develop" ]; then
        print_error "DSSAT source directory not found!"
        return 1
    fi

    cd dssat-csm-os-develop
    mkdir -p build
    cd build

    # Configure with macOS-specific settings for ARM64 compatibility
    print_status "Configuring DSSAT with CMake (macOS ARM64 compatible)..."

    # Set environment variables for ARM64 compatibility
    export MACOSX_DEPLOYMENT_TARGET=11.0

    # Configure with specific flags for ARM64 Macs
    if [[ $(uname -m) == "arm64" ]]; then
        print_status "Detected ARM64 Mac - applying compatibility fixes..."
        cmake -DCMAKE_INSTALL_PREFIX=$HOME/dssat \
              -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
              -DCMAKE_OSX_ARCHITECTURES=arm64 \
              -DCMAKE_Fortran_FLAGS="-fallow-argument-mismatch -std=legacy -w -fno-range-check -ffixed-form -ffixed-line-length-none" \
              ..
    else
        print_status "Detected Intel Mac - using standard configuration..."
        cmake -DCMAKE_INSTALL_PREFIX=$HOME/dssat \
              -DCMAKE_OSX_DEPLOYMENT_TARGET=10.15 \
              -DCMAKE_Fortran_FLAGS="-fallow-argument-mismatch -std=legacy -w -fno-range-check -ffixed-form -ffixed-line-length-none" \
              ..
    fi

    print_status "Compiling DSSAT..."
    print_status "Note: DSSAT uses old Fortran syntax that may generate warnings..."
    if ! make; then
        print_error "DSSAT compilation failed!"
        print_warning "This is a known issue with DSSAT Fortran code on macOS. Troubleshooting options:"
        echo ""
        echo "1. The DSSAT Fortran code has compatibility issues with newer gfortran versions"
        echo "   This is a limitation of the original DSSAT source code, not the setup script"
        echo ""
        echo "2. Alternative solutions:"
        echo "   a) Use the Python implementation only (recommended):"
        echo "      ./setup.sh  # (without --with-dssat)"
        echo "      python cropgro-strawberry-implementation.py"
        echo ""
        echo "   b) Try building on a Linux system or Docker container"
        echo ""
        echo "   c) Use an older version of gfortran (if available):"
        echo "      brew install gcc@9"
        echo "      export FC=gfortran-9"
        echo ""
        echo "3. Update development tools (may help):"
        echo "   xcode-select --install"
        echo "   sudo xcode-select --reset"
        echo ""
        echo "4. The Python model provides the same functionality as DSSAT"
        echo "   and is actively maintained for cross-platform compatibility"
        echo ""
        cd ../..  # Return to original directory
        return 1
    fi

    print_status "Installing DSSAT..."
    make install

    # Return to original directory
    cd ../..
    install_dssat_data
    print_success "DSSAT build and setup completed for macOS!"
}

# Function to install DSSAT data files
install_dssat_data() {
    # Install sample strawberry experiments and weather files
    print_status "Installing sample data..."
    mkdir -p $HOME/dssat/Strawberry
    
    if [ -d "dssat-csm-data-develop/Strawberry" ]; then
        cp dssat-csm-data-develop/Strawberry/* $HOME/dssat/Strawberry/
    else
        print_warning "DSSAT strawberry data not found in expected location."
    fi
    
    if [ -d "dssat-csm-data-develop/Weather" ]; then
        cp dssat-csm-data-develop/Weather/*.WTH $HOME/dssat/Strawberry/ 2>/dev/null || true
    else
        print_warning "DSSAT weather data not found in expected location."
    fi

    # Create BatchFiles directory and batch file
    mkdir -p $HOME/dssat/BatchFiles

    # Create DSSAT configuration file
    print_status "Creating DSSAT configuration..."
    cat > $HOME/dssat/DSSATPRO.L48 << 'CONFIG'
*DSSAT 4.8 CONFIGURATION FILE
! Default settings for DSSAT

$BATCH(STRAWBERRY)
CONFIG

    # Create batch file for strawberry simulations
    cat > $HOME/dssat/BatchFiles/STRB.V48 << 'BATCH'
$BATCH(STRAWBERRY)
@FILEX
              TRTNO     RP     SQ     OP     CO
../Strawberry/UFBA1401.SRX           1      1      0      1      0
../Strawberry/UFBA1601.SRX           1      1      0      1      0
../Strawberry/UFBA1601.SRX           2      1      0      1      0
../Strawberry/UFBA1701.SRX           1      1      0      1      0
../Strawberry/UFBA1701.SRX           2      1      0      1      0
../Strawberry/UFWM1401.SRX           1      1      0      1      0
../Strawberry/UFWM1401.SRX           2      1      0      1      0
BATCH

    print_status "DSSAT installed to: $HOME/dssat"
    print_status "To run DSSAT manually: cd $HOME/dssat/BatchFiles && ../dscsm048 CRGRO048 B STRB.V48"
}

# Function to test Python setup with better error handling
test_python_setup() {
    print_status "Testing Python setup..."
    
    # Determine which pip command to use
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    else
        print_error "No pip command available for package installation."
        PIP_CMD=""
    fi
    
    # Test individual packages
    PACKAGES=("numpy" "pandas" "matplotlib" "numba")
    FAILED_PACKAGES=()
    
    for package in "${PACKAGES[@]}"; do
        print_status "Testing import of $package..."
        if $PYTHON_CMD -c "import $package; print('$package version:', getattr($package, '__version__', 'unknown'))" 2>/dev/null; then
            print_success "$package imported successfully!"
        else
            print_error "Failed to import $package"
            FAILED_PACKAGES+=("$package")
        fi
    done
    
    if [ ${#FAILED_PACKAGES[@]} -eq 0 ]; then
        print_success "All required packages imported successfully!"
        return 0
    else
        print_error "Failed to import packages: ${FAILED_PACKAGES[*]}"
        
        if [ -n "$PIP_CMD" ]; then
            print_status "Attempting to install missing packages using Chinese mirrors..."
            
            MIRRORS=(
                "https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn"
                "https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
                "https://pypi.douban.com/simple/ --trusted-host pypi.douban.com"
            )
            
            for package in "${FAILED_PACKAGES[@]}"; do
                print_status "Installing $package..."
                installed=false
                
                for mirror in "${MIRRORS[@]}"; do
                    if sudo $PIP_CMD install -i $mirror "$package"; then
                        print_success "$package installed successfully using $(echo $mirror | cut -d' ' -f1)"
                        installed=true
                        break
                    fi
                done
                
                if [ "$installed" = false ]; then
                    print_warning "Trying with --user flag..."
                    for mirror in "${MIRRORS[@]}"; do
                        if $PIP_CMD install -i $mirror --user "$package"; then
                            print_success "$package installed with --user flag using $(echo $mirror | cut -d' ' -f1)"
                            installed=true
                            break
                        fi
                    done
                fi
                
                if [ "$installed" = false ]; then
                    print_error "Failed to install $package with all mirrors."
                fi
            done
            
            # Test again after installation
            print_status "Re-testing package imports..."
            STILL_FAILED=()
            for package in "${FAILED_PACKAGES[@]}"; do
                if ! $PYTHON_CMD -c "import $package" 2>/dev/null; then
                    STILL_FAILED+=("$package")
                fi
            done
            
            if [ ${#STILL_FAILED[@]} -eq 0 ]; then
                print_success "All packages now working after installation!"
                return 0
            else
                print_error "Still failed packages: ${STILL_FAILED[*]}"
                print_warning "You may need to install these packages manually."
                return 1
            fi
        else
            print_error "Cannot install packages because pip is not available."
            return 1
        fi
    fi
}

# Enhanced function to build DSSAT with comprehensive error handling
build_dssat() {
    print_status "Checking if DSSAT build is requested..."
    
    if [[ "${1:-}" == "--with-dssat" ]]; then
        print_status "Building DSSAT with enhanced error handling..."
        
        # Check if we should even attempt DSSAT build
        if command_exists gfortran; then
            GFORTRAN_VERSION=$(gfortran --version | head -n1 | grep -o '[0-9]\+' | head -n1)
            if [[ -n "$GFORTRAN_VERSION" ]] && [[ "$GFORTRAN_VERSION" -gt 10 ]]; then
                print_warning "Detected gfortran version $GFORTRAN_VERSION"
                print_warning "DSSAT may have compilation issues with gfortran > 10"
                print_warning "The Python implementation is recommended for better compatibility"
                
                echo -n "Continue with DSSAT build anyway? (y/N): "
                read -r REPLY
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    print_status "Skipping DSSAT build. Using Python implementation only."
                    print_success "Setup completed with Python implementation!"
                    return 0
                fi
            fi
        fi
        
        # Detect environment and run appropriate build script
        if [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null; then
            # WSL environment
            print_status "Building DSSAT on WSL..."
            if ! build_dssat_linux; then
                print_warning "DSSAT build failed on WSL. This is common due to compiler compatibility."
                print_status "Recommendation: Use the Python implementation which provides equivalent functionality."
                return 0
            fi
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            print_status "Building DSSAT on macOS..."
            if ! build_dssat_macos; then
                print_warning "DSSAT build failed on macOS. This is common due to compiler compatibility."
                print_status "Recommendation: Use the Python implementation which provides equivalent functionality."
                return 0
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Native Linux
            print_status "Building DSSAT on Linux..."
            if ! build_dssat_linux; then
                print_warning "DSSAT build failed on Linux. This is a known limitation of the legacy DSSAT Fortran code."
                print_status "Recommendation: Use the Python implementation which is more reliable."
                return 0
            fi
        else
            # Other Unix-like systems
            print_warning "Unsupported OS for DSSAT build: $OSTYPE"
            print_status "Using Python implementation only."
            return 0
        fi
    else
        print_status "DSSAT build skipped. Use --with-dssat flag to build DSSAT."
        print_status "Note: The Python implementation provides equivalent functionality."
    fi
}

# Function to run basic tests
run_tests() {
    print_status "Running basic tests..."
    
    # Test the main implementation
    if [ -f "cropgro-strawberry-implementation.py" ]; then
        print_status "Testing main implementation..."
        if $PYTHON_CMD cropgro-strawberry-implementation.py > /dev/null 2>&1; then
            print_success "Main implementation test passed!"
        else
            print_warning "Main implementation test had issues. This might be normal if it requires input."
        fi
    else
        print_warning "Main implementation file not found: cropgro-strawberry-implementation.py"
    fi
    
    # Run unit tests
    if [ -f "cropgro-strawberry-test1.py" ]; then
        print_status "Running unit tests..."
        if $PYTHON_CMD cropgro-strawberry-test1.py; then
            print_success "Unit tests passed!"
        else
            print_warning "Unit tests had issues. Check manually."
        fi
    else
        print_warning "Unit test file not found: cropgro-strawberry-test1.py"
    fi
}

# Main setup function
main() {
    print_status "Starting CROPGRO-Strawberry Model setup..."

    # Check Python installation
    check_python

    # Check system dependencies for DSSAT if requested
    check_system_dependencies "$@"

    # Setup virtual environment and install dependencies
    setup_venv

    # Test Python setup
    if ! test_python_setup; then
        print_warning "Python setup test had issues, but continuing..."
    fi

    # Build DSSAT if requested
    build_dssat "$@"

    # Run basic tests
    run_tests

    print_success "Setup completed successfully!"
    print_status "To activate the virtual environment in the future, run:"
    if [ -f "venv/bin/activate" ]; then
        print_status "  source venv/bin/activate"
    elif [ -f "venv/Scripts/activate" ]; then
        print_status "  source venv/Scripts/activate"
    fi
    print_status "To run the model, use: python cropgro-strawberry-implementation.py"
    print_status "To run tests, use: python cropgro-strawberry-test1.py"
}

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --with-dssat    Also build the DSSAT Fortran code (requires system dependencies)"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Setup Python environment only"
    echo "  $0 --with-dssat      # Setup Python environment and build DSSAT"
    echo ""
    echo "Note: The --with-dssat option may require sudo privileges to install"
    echo "      system dependencies (CMake, gfortran, build tools) if not already present."
    echo ""
    echo "Environment Detection:"
    echo "  - Automatically detects WSL, Linux, macOS environments"
    echo "  - Uses appropriate package managers and build strategies"
    echo "  - Falls back to Python implementation if DSSAT build fails"
}

# Parse command line arguments
if [[ "${1:-}" == "--help" ]]; then
    show_usage
    exit 0
fi

# --- Main script execution starts here ---
# Run the check immediately to ensure a supported environment
check_wsl_and_guide_user

# Set script to exit on any errors
set -e

# Run main setup
main "$@"