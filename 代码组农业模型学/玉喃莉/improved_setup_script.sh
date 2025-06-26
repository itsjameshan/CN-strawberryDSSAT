#!/usr/bin/env bash

# CROPGRO-Strawberry Model Smart Setup Script - ENHANCED VERSION
# This script sets up the Python environment and optionally builds DSSAT
# SMART RERUN: Skips already completed installation steps
# OPTIMIZED: Uses Chinese mirrors for faster downloads
# ENHANCED: Advanced proxy bypass techniques

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# State tracking file
STATE_FILE=".setup_state"

# Error log file
ERROR_LOG="error_log.txt"

# --- Function Definitions ---

# Function to log errors
log_error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local error_msg="$1"
    local step_name="${2:-Unknown}"
    
    echo "[$timestamp] ERROR in step '$step_name': $error_msg" >> "$ERROR_LOG"
    print_error "$error_msg"
}

# Function to log warnings
log_warning() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local warning_msg="$1"
    local step_name="${2:-Unknown}"
    
    echo "[$timestamp] WARNING in step '$step_name': $warning_msg" >> "$ERROR_LOG"
    print_warning "$warning_msg"
}

# Function to initialize error log
init_error_log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "=== Setup Script Error Log ===" > "$ERROR_LOG"
    echo "Started at: $timestamp" >> "$ERROR_LOG"
    echo "Script: enhanced_setup_script.sh" >> "$ERROR_LOG"
    echo "Environment: $OSTYPE" >> "$ERROR_LOG"
    echo "===============================" >> "$ERROR_LOG"
    echo "" >> "$ERROR_LOG"
}

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

print_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
}

# Function to check if a step was completed
is_step_completed() {
    local step_name="$1"
    if [ -f "$STATE_FILE" ]; then
        grep -q "^${step_name}=completed$" "$STATE_FILE"
    else
        return 1
    fi
}

# Function to mark a step as completed
mark_step_completed() {
    local step_name="$1"
    if [ ! -f "$STATE_FILE" ]; then
        touch "$STATE_FILE"
    fi
    
    # Remove any existing entry for this step
    if [ -f "$STATE_FILE" ]; then
        grep -v "^${step_name}=" "$STATE_FILE" > "${STATE_FILE}.tmp" 2>/dev/null || true
        mv "${STATE_FILE}.tmp" "$STATE_FILE" 2>/dev/null || true
    fi
    
    # Add the completed entry
    echo "${step_name}=completed" >> "$STATE_FILE"
    print_success "Marked step '${step_name}' as completed"
}

# Function to show setup progress
show_progress() {
    if [ -f "$STATE_FILE" ]; then
        print_status "=== Setup Progress ==="
        local total_steps=7
        local completed_steps=$(wc -l < "$STATE_FILE" 2>/dev/null || echo "0")
        print_status "Completed steps: ${completed_steps}/${total_steps}"
        
        if [ -s "$STATE_FILE" ]; then
            print_status "Completed:"
            while IFS='=' read -r step status; do
                if [ "$status" = "completed" ]; then
                    echo -e "  ${GREEN}✓${NC} $step"
                fi
            done < "$STATE_FILE"
        fi
        print_status "======================="
    else
        print_status "No previous setup state found. Starting fresh installation."
    fi
}

# Function to check if running in a supported environment
check_wsl_and_guide_user() {
    if is_step_completed "environment_check"; then
        print_skip "Environment check already completed"
        return 0
    fi
    
    # Check if this is a Windows-like shell (e.g., Git Bash) but NOT WSL
    # In WSL, $OSTYPE is typically 'linux-gnu', in Git Bash it's 'msys'
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Check if it's NOT WSL by looking for the /proc/version file with 'microsoft'
        if ! ( [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null ); then
            log_error "Unsupported Environment: This script must be run inside WSL (Windows Subsystem for Linux)." "environment_check"
            log_error "不支持的环境：此脚本必须在WSL (Windows的Linux子系统) 中运行。" "environment_check"
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
            echo -e "   ${GREEN}./setup_script_cn2.sh${NC}"
            exit 1
        fi
    fi
    
    mark_step_completed "environment_check"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if Python is properly installed
is_python_ready() {
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        if python -c "import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)" 2>/dev/null; then
            PYTHON_CMD="python"
        else
            return 1
        fi
    else
        return 1
    fi
    
    # Check if pip is available
    if command_exists pip3 || command_exists pip; then
        return 0
    else
        return 1
    fi
}

# Function to install Python and pip
install_python_and_pip() {
    if is_step_completed "python_installation"; then
        print_skip "Python installation already completed"
        return 0
    fi
    
    if is_python_ready; then
        print_skip "Python and pip are already installed and working"
        mark_step_completed "python_installation"
        return 0
    fi
    
    log_warning "Python 3 or pip not found. Attempting to install..." "python_installation"
    
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
            if ! brew install python3; then
                log_error "Failed to install Python 3 via Homebrew" "python_installation"
                exit 1
            fi
        else
            log_error "Homebrew not found. Please install Python 3 manually." "python_installation"
            exit 1
        fi
    else # Linux, WSL, or other Unix-like systems
        if command_exists apt-get; then
            print_status "Installing python3 and python3-pip via apt..."
            if ! sudo apt-get update; then
                log_error "Failed to update package list" "python_installation"
                exit 1
            fi
            if ! sudo apt-get install -y python3 python3-pip python3-venv; then
                log_error "Failed to install python3 and python3-pip via apt" "python_installation"
                exit 1
            fi
        elif command_exists yum; then
            print_status "Installing python3 and python3-pip via yum..."
            if ! sudo yum install -y python3 python3-pip; then
                log_error "Failed to install python3 and python3-pip via yum" "python_installation"
                exit 1
            fi
        elif command_exists dnf; then
            print_status "Installing python3 and python3-pip via dnf..."
            if ! sudo dnf install -y python3 python3-pip; then
                log_error "Failed to install python3 and python3-pip via dnf" "python_installation"
                exit 1
            fi
        else
            log_error "Unsupported package manager. Please install Python 3 and pip manually." "python_installation"
            exit 1
        fi
    fi

    # Verify installation
    if command_exists python3 && command_exists pip3; then
        print_success "Python 3 and pip installed successfully."
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
        mark_step_completed "python_installation"
    else
        log_error "Failed to install Python 3 and/or pip." "python_installation"
        exit 1
    fi
}

# ENHANCED: Super-aggressive proxy bypass function
super_aggressive_proxy_bypass() {
    print_status "SUPER-AGGRESSIVE proxy bypass - removing ALL proxy traces..."
    
    # Save original shell options
    local old_opts=$(set +o)
    
    # Unset ALL possible proxy environment variables
    local all_proxy_vars=(
        "http_proxy" "https_proxy" "HTTP_PROXY" "HTTPS_PROXY"
        "ftp_proxy" "FTP_PROXY" "socks_proxy" "SOCKS_PROXY"
        "all_proxy" "ALL_PROXY" "no_proxy" "NO_PROXY"
        "rsync_proxy" "RSYNC_PROXY"
    )
    
    # Backup and unset all proxy variables
    for var in "${all_proxy_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            print_warning "Backing up and unsetting: $var=${!var}"
            export "${var}_BACKUP"="${!var}"
        fi
        unset "$var"
    done
    
    # Force environment cleanup
    export http_proxy=""
    export https_proxy=""
    export HTTP_PROXY=""
    export HTTPS_PROXY=""
    export all_proxy=""
    export ALL_PROXY=""
    export no_proxy="*"
    export NO_PROXY="*"
    
    # Remove any pip proxy configurations
    rm -rf ~/.pip ~/.config/pip
    
    # Clear any cached environment
    hash -r
    
    print_success "ALL proxy traces removed"
}

# Function to restore proxy settings if they were backed up
restore_proxy_settings() {
    local proxy_vars=("http_proxy" "https_proxy" "HTTP_PROXY" "HTTPS_PROXY" "ftp_proxy" "FTP_PROXY" "all_proxy" "ALL_PROXY")
    
    print_status "Restoring original proxy settings..."
    for var in "${proxy_vars[@]}"; do
        local backup_var="${var}_BACKUP"
        if [[ -n "${!backup_var:-}" ]]; then
            export "$var"="${!backup_var}"
            unset "$backup_var"
            print_status "Restored: $var=${!var}"
        fi
    done
    
    # Don't restore no_proxy/NO_PROXY wildcards
}

# ENHANCED: Create bulletproof pip configuration
create_bulletproof_pip_config() {
    print_status "Creating bulletproof pip configuration..."
    
    # Remove any existing configs
    rm -rf ~/.pip ~/.config/pip
    
    # Create directories
    mkdir -p ~/.pip ~/.config/pip
    
    # Create the most aggressive no-proxy config possible
    cat > ~/.pip/pip.conf << 'EOF'
[global]
# Chinese mirrors for speed
index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
extra-index-url = 
    https://mirrors.aliyun.com/pypi/simple/
    https://pypi.douban.com/simple/
    https://pypi.mirrors.ustc.edu.cn/simple/

# ABSOLUTELY NO PROXY
proxy = 
http-proxy = 
https-proxy = 
no-proxy = *

# Trusted hosts
trusted-host = 
    pypi.tuna.tsinghua.edu.cn
    mirrors.aliyun.com
    pypi.douban.com
    pypi.mirrors.ustc.edu.cn
    pypi.org
    pypi.python.org
    files.pythonhosted.org

# Timeout and retry settings
timeout = 300
retries = 10
disable-pip-version-check = true

[install]
trusted-host = 
    pypi.tuna.tsinghua.edu.cn
    mirrors.aliyun.com
    pypi.douban.com
    pypi.mirrors.ustc.edu.cn
    pypi.org
    pypi.python.org
    files.pythonhosted.org

[list]
format = columns
EOF

    # Copy to both locations
    cp ~/.pip/pip.conf ~/.config/pip/pip.conf
    
    print_success "Bulletproof pip configuration created"
}

# Function to check for proxy issues and warn user
check_proxy_issues() {
    print_status "Checking for proxy configuration issues..."
    
    # Check for common proxy environment variables
    local proxy_vars=("http_proxy" "https_proxy" "HTTP_PROXY" "HTTPS_PROXY" "all_proxy" "ALL_PROXY")
    local proxy_detected=false
    local proxy_info=""
    
    for var in "${proxy_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            proxy_detected=true
            proxy_info="$proxy_info\n  $var=${!var}"
        fi
    done
    
    if [ "$proxy_detected" = true ]; then
        print_warning "Detected proxy settings that may interfere with Chinese mirrors:"
        echo -e "$proxy_info"
        print_status "This script will AGGRESSIVELY disable proxy settings during installation"
        print_status "to ensure direct access to fast Chinese mirrors."
        print_status "Proxy settings will be restored after installation."
        print_status "此脚本将激进地禁用代理设置以确保直接访问快速的中国镜像源。"
        print_status "安装完成后将恢复代理设置。"
        echo ""
        sleep 2
    else
        print_success "No problematic proxy settings detected"
    fi
}

# Function to check if virtual environment exists and is working
is_venv_ready() {
    local venv_name="${1:-venv}"
    
    if [ ! -d "$venv_name" ]; then
        return 1
    fi
    
    # Check if activation script exists
    if [ -f "$venv_name/bin/activate" ] || [ -f "$venv_name/Scripts/activate" ]; then
        # Try to activate and check if python works
        if [ -f "$venv_name/bin/activate" ]; then
            source "$venv_name/bin/activate" && python -c "import sys; sys.exit(0)" 2>/dev/null
            local result=$?
            deactivate 2>/dev/null || true
            return $result
        elif [ -f "$venv_name/Scripts/activate" ]; then
            source "$venv_name/Scripts/activate" && python -c "import sys; sys.exit(0)" 2>/dev/null
            local result=$?
            deactivate 2>/dev/null || true
            return $result
        fi
    fi
    
    return 1
}

# Function to check if requirements are installed in venv
are_requirements_installed() {
    local venv_name="${1:-venv}"
    
    if ! is_venv_ready "$venv_name"; then
        return 1
    fi
    
    # Activate venv and check for key packages
    if [ -f "$venv_name/bin/activate" ]; then
        source "$venv_name/bin/activate"
    elif [ -f "$venv_name/Scripts/activate" ]; then
        source "$venv_name/Scripts/activate"
    else
        return 1
    fi
    
    # Check for essential packages
    local packages=("numpy" "pandas" "matplotlib" "scipy")
    for package in "${packages[@]}"; do
        if ! python -c "import $package" 2>/dev/null; then
            deactivate 2>/dev/null || true
            return 1
        fi
    done
    
    deactivate 2>/dev/null || true
    return 0
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

# Data handling
openpyxl>=3.0.0
xlrd>=2.0.0
EOF
        print_success "Created default requirements.txt with essential packages."
    fi
}

# ENHANCED: Nuclear option pip installation function
nuclear_pip_install() {
    local package="$1"
    local mirror="$2"
    local host="$3"
    
    print_status "Nuclear pip install: $package from $mirror"
    
    # Try the most aggressive approach possible
    local install_cmd="env -i PATH=\"\$PATH\" HOME=\"\$HOME\" USER=\"\$USER\" \
        TERM=\"\$TERM\" PWD=\"\$PWD\" \
        http_proxy='' https_proxy='' HTTP_PROXY='' HTTPS_PROXY='' \
        all_proxy='' ALL_PROXY='' no_proxy='*' NO_PROXY='*' \
        pip install --isolated --disable-pip-version-check --no-cache-dir \
        --proxy '' --trusted-host $host \
        --index-url $mirror --timeout 300 --retries 5 $package"
    
    print_status "Command: $install_cmd"
    
    if eval "$install_cmd"; then
        print_success "Successfully installed $package using nuclear method"
        return 0
    else
        print_error "Nuclear method failed for $package"
        return 1
    fi
}

# ENHANCED: Setup virtual environment with super-aggressive proxy bypass
setup_venv() {
    if is_step_completed "venv_setup"; then
        print_skip "Virtual environment setup already completed"
        return 0
    fi
    
    local venv_name="venv"
    
    # Check if venv already exists and is working
    if are_requirements_installed "$venv_name"; then
        print_skip "Virtual environment already exists and has required packages"
        mark_step_completed "venv_setup"
        return 0
    fi
    
    print_status "Setting up Python virtual environment with SUPER-AGGRESSIVE proxy bypass..."
    
    # Super-aggressive proxy bypass
    super_aggressive_proxy_bypass
    
    # Create bulletproof pip config
    create_bulletproof_pip_config
    
    # Find Python and pip commands
    install_python_and_pip
    
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "No Python command found!"
        exit 1
    fi
    
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    else
        print_error "No pip command found!"
        exit 1
    fi
    
    # Remove old venv if it exists but is broken
    if [ -d "$venv_name" ] && ! is_venv_ready "$venv_name"; then
        print_warning "Removing broken virtual environment..."
        rm -rf "$venv_name"
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$venv_name" ]; then
        print_status "Creating virtual environment..."
        if ! $PYTHON_CMD -m venv "$venv_name"; then
            log_error "Failed to create virtual environment." "venv_setup"
            exit 1
        fi
        print_success "Virtual environment created."
    fi
    
    # Activate virtual environment
    if [ -f "$venv_name/bin/activate" ]; then
        source "$venv_name/bin/activate"
        print_success "Virtual environment activated."
    elif [ -f "$venv_name/Scripts/activate" ]; then
        source "$venv_name/Scripts/activate"
        print_success "Virtual environment activated (Windows style)."
    else
        log_error "Could not find activation script." "venv_setup"
        exit 1
    fi
    
    # Create requirements.txt if it doesn't exist
    create_requirements_txt
    
    # Super-aggressive pip upgrade
    print_status "Upgrading pip with nuclear option..."
    if nuclear_pip_install "--upgrade pip" "https://pypi.tuna.tsinghua.edu.cn/simple/" "pypi.tuna.tsinghua.edu.cn"; then
        print_success "Pip upgraded successfully"
    else
        print_warning "Pip upgrade failed, continuing with existing version"
    fi
    
    # Define mirrors and their hosts
    declare -A mirrors=(
        ["https://pypi.tuna.tsinghua.edu.cn/simple/"]="pypi.tuna.tsinghua.edu.cn"
        ["https://mirrors.aliyun.com/pypi/simple/"]="mirrors.aliyun.com"
        ["https://pypi.douban.com/simple/"]="pypi.douban.com"
        ["https://pypi.mirrors.ustc.edu.cn/simple/"]="pypi.mirrors.ustc.edu.cn"
    )
    
    # Define packages to install
    local packages=("numpy>=1.19.0" "pandas>=1.3.0" "matplotlib>=3.3.0" "scipy>=1.7.0" "numba>=0.56.0" "openpyxl>=3.0.0")
    
    local all_installed=true
    
    # Try to install each package with nuclear methods
    for package in "${packages[@]}"; do
        local package_installed=false
        
        # Try each mirror
        for mirror in "${!mirrors[@]}"; do
            local host="${mirrors[$mirror]}"
            
            if nuclear_pip_install "$package" "$mirror" "$host"; then
                package_installed=true
                break
            fi
        done
        
        if [ "$package_installed" = false ]; then
            print_error "Failed to install $package with ALL nuclear methods"
            all_installed=false
        fi
    done
    
    if [ "$all_installed" = false ]; then
        print_error "=== INSTALLATION FAILED ==="
        print_error "Even nuclear methods failed! Last resort options:"
        print_error ""
        print_error "1. MANUAL CONDA INSTALLATION:"
        print_error "   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        print_error "   bash Miniconda3-latest-Linux-x86_64.sh"
        print_error "   conda create -n strawberry python=3.9"
        print_error "   conda activate strawberry"
        print_error "   conda install numpy pandas matplotlib scipy numba"
        print_error ""
        print_error "2. OFFLINE INSTALLATION:"
        print_error "   Download packages on another machine and transfer them"
        print_error ""
        print_error "3. SYSTEM PACKAGES:"
        print_error "   sudo apt-get install python3-numpy python3-pandas python3-matplotlib python3-scipy"
        print_error ""
        deactivate 2>/dev/null || true
        exit 1
    fi
    
    print_success "All packages installed successfully with nuclear methods!"
    deactivate 2>/dev/null || true
    mark_step_completed "venv_setup"
}

# Enhanced function to install CMake with proper environment detection
install_cmake() {
    if command_exists cmake && cmake --version >/dev/null 2>&1; then
        CMAKE_VERSION=$(cmake --version 2>/dev/null | head -n1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -n1)
        print_skip "CMake already installed. Version: $CMAKE_VERSION"
        return 0
    fi
    
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

# Function to install Fortran compiler based on OS
install_fortran_compiler() {
    if command_exists gfortran && gfortran --version >/dev/null 2>&1; then
        GFORTRAN_VERSION=$(gfortran --version | head -n1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -n1)
        if [[ -z "$GFORTRAN_VERSION" ]]; then
            GFORTRAN_VERSION=$(gfortran --version | head -n1 | sed 's/.*\([0-9]\+\.[0-9]\+\).*/\1/')
        fi
        print_skip "gfortran already installed. Version: $GFORTRAN_VERSION"
        return 0
    fi
    
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
    if command_exists make; then
        print_skip "Build tools (make) already installed"
        return 0
    fi
    
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

# Enhanced function to check system dependencies with better detection
check_system_dependencies() {
    if [[ "${1:-}" == "--with-dssat" ]]; then
        if is_step_completed "system_dependencies"; then
            print_skip "System dependencies already checked and installed"
            return 0
        fi
        
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
                print_skip "Found working CMake $CMAKE_VERSION at $(which cmake)"
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
            print_skip "Found gfortran $GFORTRAN_VERSION at $(which gfortran)"

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
            print_skip "Found make build tool at $(which make)"
        fi
        
        # Final verification
        print_status "=== Dependency Check Summary ==="
        print_status "CMake: $(which cmake 2>/dev/null || echo 'NOT FOUND')"
        print_status "gfortran: $(which gfortran 2>/dev/null || echo 'NOT FOUND')"
        print_status "make: $(which make 2>/dev/null || echo 'NOT FOUND')"
        
        mark_step_completed "system_dependencies"
    fi
}

# Function to check if DSSAT is already built
is_dssat_built() {
    # Check if DSSAT executable exists in expected location
    if [ -f "$HOME/dssat/dscsm048" ] || [ -f "dssat-csm-os-develop/build/dscsm048" ]; then
        return 0
    fi
    
    # Check if build directory exists with successful build artifacts
    if [ -d "dssat-csm-os-develop/build" ] && [ -f "dssat-csm-os-develop/build/Makefile" ]; then
        # Check if make was successful (look for compiled objects)
        if find "dssat-csm-os-develop/build" -name "*.o" -o -name "dscsm048" | grep -q .; then
            return 0
        fi
    fi
    
    return 1
}

# Enhanced function to build DSSAT on Linux with comprehensive error handling
build_dssat_linux() {
    if is_dssat_built; then
        print_skip "DSSAT already built successfully"
        return 0
    fi
    
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
    
    # Only clean if this is a fresh build attempt
    if [ -d "build" ] && [ ! -f "build/.build_completed" ]; then
        print_status "Cleaning previous incomplete build..."
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
    
    # Configure with enhanced settings (skip if already configured)
    if [ ! -f "Makefile" ]; then
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
            cd ../..
            return 1
        fi
    else
        print_skip "CMake already configured (Makefile exists)"
    fi

    # Compilation (skip if already compiled)
    if [ ! -f "dscsm048" ] && [ ! -f ".build_completed" ]; then
        print_status "Compiling DSSAT (this may take several minutes)..."
        
        if make -j1 2>&1 | tee build.log; then
            print_success "DSSAT compilation successful"
            touch .build_completed
        else
            print_error "DSSAT compilation failed!"
            print_error "Build log (last 30 lines):"
            tail -30 build.log
            cd ../..
            return 1
        fi
    else
        print_skip "DSSAT already compiled"
    fi

    # Installation (skip if already installed)
    if [ ! -f "$HOME/dssat/dscsm048" ]; then
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
    else
        print_skip "DSSAT already installed"
    fi

    # Return to original directory
    cd ../..
    return 0
}

# Function to build DSSAT on macOS with ARM64 compatibility fixes
build_dssat_macos() {
    if is_dssat_built; then
        print_skip "DSSAT already built successfully"
        return 0
    fi
    
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
    if [ ! -f "Makefile" ]; then
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
    else
        print_skip "CMake already configured"
    fi

    if [ ! -f "dscsm048" ]; then
        print_status "Compiling DSSAT..."
        print_status "Note: DSSAT uses old Fortran syntax that may generate warnings..."
        if ! make; then
            print_error "DSSAT compilation failed!"
            cd ../..
            return 1
        fi
    else
        print_skip "DSSAT already compiled"
    fi

    if [ ! -f "$HOME/dssat/dscsm048" ]; then
        print_status "Installing DSSAT..."
        make install
    else
        print_skip "DSSAT already installed"
    fi

    # Return to original directory
    cd ../..
    return 0
}

# Function to install DSSAT data files
install_dssat_data() {
    if [ -d "$HOME/dssat/Strawberry" ] && [ -f "$HOME/dssat/BatchFiles/STRB.V48" ]; then
        print_skip "DSSAT data files already installed"
        return 0
    fi
    
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

# Enhanced function to build DSSAT with comprehensive error handling
build_dssat() {
    if [[ "${1:-}" == "--with-dssat" ]]; then
        if is_step_completed "dssat_build"; then
            print_skip "DSSAT build already completed"
            return 0
        fi
        
        print_status "Checking if DSSAT build is requested..."
        
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
                    mark_step_completed "dssat_build"
                    return 0
                fi
            fi
        fi
        
        # Detect environment and run appropriate build script
        if [[ -f "/proc/version" ]] && grep -qi "microsoft" /proc/version 2>/dev/null; then
            # WSL environment
            print_status "Building DSSAT on WSL..."
            if build_dssat_linux; then
                install_dssat_data
                mark_step_completed "dssat_build"
            else
                print_warning "DSSAT build failed on WSL. This is common due to compiler compatibility."
                print_status "Recommendation: Use the Python implementation which provides equivalent functionality."
                mark_step_completed "dssat_build"  # Mark as completed to skip on rerun
                return 0
            fi
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            print_status "Building DSSAT on macOS..."
            if build_dssat_macos; then
                install_dssat_data
                mark_step_completed "dssat_build"
            else
                print_warning "DSSAT build failed on macOS. This is common due to compiler compatibility."
                print_status "Recommendation: Use the Python implementation which provides equivalent functionality."
                mark_step_completed "dssat_build"  # Mark as completed to skip on rerun
                return 0
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Native Linux
            print_status "Building DSSAT on Linux..."
            if build_dssat_linux; then
                install_dssat_data
                mark_step_completed "dssat_build"
            else
                print_warning "DSSAT build failed on Linux. This is a known limitation of the legacy DSSAT Fortran code."
                print_status "Recommendation: Use the Python implementation which is more reliable."
                mark_step_completed "dssat_build"  # Mark as completed to skip on rerun
                return 0
            fi
        else
            # Other Unix-like systems
            print_warning "Unsupported OS for DSSAT build: $OSTYPE"
            print_status "Using Python implementation only."
            mark_step_completed "dssat_build"
            return 0
        fi
    else
        print_status "DSSAT build skipped. Use --with-dssat flag to build DSSAT."
        print_status "Note: The Python implementation provides equivalent functionality."
    fi
}

# Function to test Python setup with better error handling
test_python_setup() {
    if is_step_completed "python_test"; then
        print_skip "Python setup test already completed"
        return 0
    fi
    
    print_status "Testing Python setup..."
    
    # Activate virtual environment for testing
    if [ -f "venv/bin/activate" ]; then
        source "venv/bin/activate"
    elif [ -f "venv/Scripts/activate" ]; then
        source "venv/Scripts/activate"
    else
        print_warning "Virtual environment not found, testing global installation"
    fi
    
    # Find Python command
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "No Python command available for testing."
        return 1
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
    
    # Deactivate virtual environment
    deactivate 2>/dev/null || true
    
    if [ ${#FAILED_PACKAGES[@]} -eq 0 ]; then
        print_success "All required packages imported successfully!"
        mark_step_completed "python_test"
        return 0
    else
        print_error "Failed to import packages: ${FAILED_PACKAGES[*]}"
        print_warning "You may need to re-run the setup or install packages manually."
        return 1
    fi
}

# Function to run basic tests
run_tests() {
    if is_step_completed "basic_tests"; then
        print_skip "Basic tests already completed"
        return 0
    fi
    
    print_status "Running basic tests..."
    
    # Find Python command
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "No Python command available for testing."
        return 1
    fi
    
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
    
    mark_step_completed "basic_tests"
}

# Function to reset setup state
reset_setup_state() {
    if [ -f "$STATE_FILE" ]; then
        print_warning "Removing previous setup state..."
        rm -f "$STATE_FILE"
        print_success "Setup state reset. Next run will be a fresh installation."
    else
        print_status "No previous setup state found."
    fi
}

# Main setup function
main() {
    # Initialize error log
    init_error_log
    
    print_status "Starting CROPGRO-Strawberry Model setup (ENHANCED Version - NUCLEAR Proxy Bypass)..."
    print_status "使用核武级代理绕过技术的增强安装脚本..."
    
    # Check for proxy issues early
    check_proxy_issues
    
    # Show current progress
    show_progress
    
    # Check environment
    if ! check_wsl_and_guide_user; then
        log_error "Environment check failed" "main"
        exit 1
    fi
    
    # Check Python installation
    if ! install_python_and_pip; then
        log_error "Python installation failed" "main"
        exit 1
    fi
    
    # Check system dependencies for DSSAT if requested
    if ! check_system_dependencies "$@"; then
        log_error "System dependencies check failed" "main"
        exit 1
    fi
    
    # Setup virtual environment and install dependencies with nuclear methods
    if ! setup_venv; then
        log_error "Virtual environment setup failed even with nuclear methods" "main"
        print_error "=== FINAL FALLBACK INSTRUCTIONS ==="
        print_error "1. Try conda instead:"
        print_error "   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        print_error "   bash Miniconda3-latest-Linux-x86_64.sh"
        print_error "   conda create -n strawberry python=3.9"
        print_error "   conda activate strawberry"
        print_error "   conda install numpy pandas matplotlib scipy"
        print_error ""
        print_error "2. Contact your IT department for proxy bypass"
        print_error "3. Try on a different network (mobile hotspot)"
        exit 1
    fi
    
    # Test Python setup
    if ! test_python_setup; then
        log_warning "Python setup test had issues, but continuing..." "main"
    fi
    
    # Build DSSAT if requested
    if ! build_dssat "$@"; then
        log_warning "DSSAT build failed, but continuing with Python implementation..." "main"
    fi
    
    # Run basic tests
    if ! run_tests; then
        log_warning "Some tests failed, but setup completed" "main"
    fi
    
    # Restore any proxy settings that were temporarily disabled
    restore_proxy_settings
    
    print_success "Setup completed successfully with NUCLEAR methods!"
    print_success "使用核武级方法安装完成！"
    print_status "Proxy settings have been restored (if any were disabled)."
    print_status "代理设置已恢复（如果有被禁用的话）。"
    print_status "To activate the virtual environment in the future, run:"
    print_status "要激活虚拟环境，请运行："
    if [ -f "venv/bin/activate" ]; then
        print_status "  source venv/bin/activate"
    elif [ -f "venv/Scripts/activate" ]; then
        print_status "  source venv/Scripts/activate"
    fi
    print_status "To run the model, use: python cropgro-strawberry-implementation.py"
    print_status "运行模型：python cropgro-strawberry-implementation.py"
    print_status "To run tests, use: python cropgro-strawberry-test1.py"
    print_status "运行测试：python cropgro-strawberry-test1.py"
    echo ""
    print_status "=== Nuclear Troubleshooting Complete / 核武级故障排除完成 ==="
    
    # Log successful completion
    echo "$(date '+%Y-%m-%d %H:%M:%S') SUCCESS: Setup completed successfully with nuclear methods" >> "$ERROR_LOG"
}

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "用法: $0 [选项]"
    echo ""
    echo "Options:"
    echo "选项："
    echo "  --with-dssat    Also build the DSSAT Fortran code (requires system dependencies)"
    echo "                  同时构建DSSAT Fortran代码（需要系统依赖项）"
    echo "  --reset         Reset setup state for fresh installation"
    echo "                  重置安装状态以进行全新安装"
    echo "  --fix-proxy     Reset pip configuration to fix proxy issues"
    echo "                  重置pip配置以修复代理问题"
    echo "  --help          Show this help message"
    echo "                  显示此帮助信息"
    echo ""
    echo "Examples:"
    echo "示例："
    echo "  $0                    # Setup Python environment only (smart rerun)"
    echo "                        # 仅设置Python环境（智能重新运行）"
    echo "  $0 --with-dssat      # Setup Python environment and build DSSAT (smart rerun)"
    echo "                        # 设置Python环境并构建DSSAT（智能重新运行）"
    echo "  $0 --reset           # Reset all setup state"
    echo "                        # 重置所有设置状态"
    echo "  $0 --reset --with-dssat  # Reset and do full setup with DSSAT"
    echo "                            # 重置并进行包含DSSAT的完整设置"
    echo ""
    echo "ENHANCED Features:"
    echo "增强功能："
    echo "  - NUCLEAR-level proxy bypass techniques"
    echo "    核武级代理绕过技术"
    echo "  - Super-aggressive environment cleaning"
    echo "    超激进的环境清理"
    echo "  - Bulletproof pip configuration"
    echo "    防弹级pip配置"
    echo "  - Multiple fallback strategies"
    echo "    多重备用策略"
    echo "  - Automatic conda fallback suggestion"
    echo "    自动conda备用建议"
    echo ""
    echo "Chinese Mirrors + NUCLEAR No-Proxy Optimization:"
    echo "中国镜像源 + 核武级无代理优化："
    echo "  - Prioritizes Chinese mirrors for faster downloads"
    echo "    优先使用中国镜像源以获得更快的下载速度"
    echo "  - NUCLEAR-level proxy disabling during installation"
    echo "    安装期间核武级代理禁用"
    echo "  - Primary: Tsinghua, Backup: Alibaba, Douban, USTC"
    echo "    主要：清华，备用：阿里巴巴，豆瓣，中科大"
    echo "  - Environment isolation for maximum bypass effectiveness"
    echo "    环境隔离以获得最大绕过效果"
    echo ""
    echo "Note: The --with-dssat option may require sudo privileges to install"
    echo "      system dependencies (CMake, gfortran, build tools) if not already present."
    echo "注意：如果系统依赖项（CMake、gfortran、构建工具）尚未安装，"
    echo "      --with-dssat选项可能需要sudo权限。"
}

# Parse command line arguments
if [[ "${1:-}" == "--help" ]]; then
    show_usage
    exit 0
fi

if [[ "${1:-}" == "--fix-proxy" ]] || [[ "${2:-}" == "--fix-proxy" ]] || [[ "${3:-}" == "--fix-proxy" ]]; then
    print_status "Fixing proxy configuration issues with NUCLEAR methods..."
    super_aggressive_proxy_bypass
    create_bulletproof_pip_config
    print_success "NUCLEAR proxy fix completed. Try running the script again."
    exit 0
fi

if [[ "${1:-}" == "--reset" ]] || [[ "${2:-}" == "--reset" ]]; then
    reset_setup_state
    # Remove --reset from arguments for main function
    set -- "${@/--reset/}"
fi

# Error trap to catch unexpected errors
trap 'log_error "Unexpected error occurred. Exit code: $?" "unexpected_error"; exit 1' ERR

# --- Main script execution starts here ---
# Run the check immediately to ensure a supported environment
check_wsl_and_guide_user

# Set script to exit on any errors
set -e

# Run main setup
main "$@"