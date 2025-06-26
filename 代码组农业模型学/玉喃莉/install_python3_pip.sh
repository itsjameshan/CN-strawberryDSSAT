#!/usr/bin/env bash

# Python3-pip 安装脚本 / Python3-pip Installation Script
# 解决 "E: Package 'python3-pip' has no installation candidate" 问题

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to test network connectivity
test_network() {
    print_status "Testing network connectivity..."
    
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        print_success "Network connectivity: OK"
        return 0
    else
        print_error "Network connectivity: FAILED"
        return 1
    fi
}

# Function to configure apt mirrors
configure_apt_mirrors() {
    print_status "Configuring apt mirrors for better package availability..."
    
    # Backup original sources list
    if [[ -f /etc/apt/sources.list ]]; then
        sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)
        print_status "Backed up original sources.list"
    fi
    
    # Detect Ubuntu/Debian version
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        OS_NAME="$ID"
        OS_VERSION="$VERSION_ID"
        print_status "Detected: $OS_NAME $OS_VERSION"
    else
        print_warning "Cannot detect OS version"
        return 1
    fi
    
    # Define reliable mirrors
    case "$OS_NAME" in
        "ubuntu")
            MIRROR_URL="https://mirrors.aliyun.com/ubuntu/"
            MIRROR_NAME="阿里云镜像源"
            ;;
        "debian")
            MIRROR_URL="https://mirrors.aliyun.com/debian/"
            MIRROR_NAME="阿里云镜像源"
            ;;
        *)
            print_warning "Unsupported OS: $OS_NAME"
            return 1
            ;;
    esac
    
    # Update sources.list
    print_status "Updating sources.list with $MIRROR_NAME..."
    
    sudo tee /etc/apt/sources.list > /dev/null << EOF
# Updated by install script with $MIRROR_NAME
deb $MIRROR_URL $OS_VERSION main restricted universe multiverse
deb $MIRROR_URL $OS_VERSION-updates main restricted universe multiverse
deb $MIRROR_URL $OS_VERSION-security main restricted universe multiverse
EOF
    
    print_success "Updated sources.list with $MIRROR_NAME"
    
    # Update package lists
    print_status "Updating package lists..."
    if sudo apt-get update; then
        print_success "Package lists updated successfully"
        return 0
    else
        print_error "Failed to update package lists"
        return 1
    fi
}

# Function to install python3-pip via apt
install_python3_pip_apt() {
    print_status "Installing python3-pip via apt-get..."
    
    # Update package lists with retry mechanism
    for attempt in 1 2 3; do
        print_status "Updating package lists (attempt $attempt/3)..."
        if sudo apt-get update; then
            print_success "Package lists updated successfully"
            break
        else
            if [ $attempt -lt 3 ]; then
                print_warning "Package list update failed. Retrying in 5 seconds..."
                sleep 5
            else
                print_error "Failed to update package lists after 3 attempts"
                print_status "Trying to configure better mirrors..."
                if configure_apt_mirrors; then
                    # Try updating again after mirror configuration
                    if sudo apt-get update; then
                        print_success "Package lists updated after mirror configuration"
                    else
                        print_error "Still failed to update package lists"
                        return 1
                    fi
                else
                    return 1
                fi
            fi
        fi
    done
    
    # Try different package names
    PIP_PACKAGES=(
        "python3-pip"
        "python3-pip3"
        "python-pip3"
        "python3-pip-whl"
    )
    
    print_status "Trying different python3-pip package names..."
    
    for package in "${PIP_PACKAGES[@]}"; do
        print_status "Checking availability of $package..."
        
        # Check if package is available
        if apt-cache search "$package" | grep -q "^$package "; then
            print_status "Package $package is available, attempting installation..."
            
            if sudo apt-get install -y "$package"; then
                print_success "$package installed successfully"
                return 0
            else
                print_warning "Failed to install $package, trying next option..."
            fi
        else
            print_warning "Package $package is not available in repositories"
        fi
    done
    
    print_error "All apt packages failed"
    return 1
}

# Function to install pip via get-pip.py
install_pip_get_pip() {
    print_status "Installing pip via get-pip.py..."
    
    # Download get-pip.py
    if command_exists curl; then
        DOWNLOAD_CMD="curl -L"
    elif command_exists wget; then
        DOWNLOAD_CMD="wget -O -"
    else
        print_error "Neither curl nor wget found"
        return 1
    fi
    
    print_status "Downloading get-pip.py..."
    
    if $DOWNLOAD_CMD https://bootstrap.pypa.io/get-pip.py > get-pip.py 2>/dev/null; then
        print_success "Downloaded get-pip.py successfully"
        
        # Install pip using python3
        if python3 get-pip.py --user; then
            print_success "pip installed successfully via get-pip.py"
            
            # Add to PATH
            export PATH="$HOME/.local/bin:$PATH"
            
            # Clean up
            rm -f get-pip.py
            
            return 0
        else
            print_error "Failed to install pip via get-pip.py"
            rm -f get-pip.py
            return 1
        fi
    else
        print_error "Failed to download get-pip.py"
        return 1
    fi
}

# Function to install pip via easy_install
install_pip_easy_install() {
    print_status "Installing pip via easy_install..."
    
    if command_exists easy_install; then
        if sudo easy_install pip; then
            print_success "pip installed successfully via easy_install"
            return 0
        else
            print_error "Failed to install pip via easy_install"
            return 1
        fi
    else
        print_warning "easy_install not found"
        return 1
    fi
}

# Function to verify pip installation
verify_pip_installation() {
    print_status "Verifying pip installation..."
    
    # Check different pip commands
    PIP_COMMANDS=("pip3" "pip" "python3 -m pip" "python -m pip")
    
    for cmd in "${PIP_COMMANDS[@]}"; do
        if command_exists "$cmd" || $cmd --version >/dev/null 2>&1; then
            PIP_VERSION=$($cmd --version 2>/dev/null | head -n1)
            print_success "Found pip: $PIP_VERSION"
            print_status "Command: $cmd"
            return 0
        fi
    done
    
    # Check in common locations
    PIP_PATHS=(
        "/usr/bin/pip3"
        "/usr/local/bin/pip3"
        "/usr/bin/pip"
        "/usr/local/bin/pip"
        "$HOME/.local/bin/pip3"
        "$HOME/.local/bin/pip"
    )
    
    for path in "${PIP_PATHS[@]}"; do
        if [[ -x "$path" ]]; then
            PIP_VERSION=$("$path" --version 2>/dev/null | head -n1)
            print_success "Found pip at: $path"
            print_status "Version: $PIP_VERSION"
            return 0
        fi
    done
    
    print_error "pip not found after installation"
    return 1
}

# Function to test pip functionality
test_pip_functionality() {
    print_status "Testing pip functionality..."
    
    # Determine which pip command to use
    PIP_CMD=""
    for cmd in "pip3" "pip" "python3 -m pip" "python -m pip"; do
        if command_exists "$cmd" || $cmd --version >/dev/null 2>&1; then
            PIP_CMD="$cmd"
            break
        fi
    done
    
    if [[ -z "$PIP_CMD" ]]; then
        print_error "No pip command found"
        return 1
    fi
    
    print_status "Using pip command: $PIP_CMD"
    
    # Test installing a simple package
    print_status "Testing package installation..."
    
    if $PIP_CMD install --user requests >/dev/null 2>&1; then
        print_success "Successfully installed requests package"
        
        # Test importing the package
        if python3 -c "import requests; print('requests version:', requests.__version__)" 2>/dev/null; then
            print_success "Successfully imported requests package"
            return 0
        else
            print_warning "Installed requests but failed to import"
            return 1
        fi
    else
        print_warning "Failed to install test package"
        return 1
    fi
}

# Main function
main() {
    print_status "Starting python3-pip installation..."
    echo ""
    
    # Check system requirements
    if ! command_exists apt-get; then
        print_error "This script is designed for Ubuntu/Debian systems"
        print_error "For other systems, please install pip manually"
        exit 1
    fi
    
    if ! command_exists python3; then
        print_error "python3 is not installed. Please install python3 first."
        exit 1
    fi
    
    print_status "Python3 version: $(python3 --version)"
    echo ""
    
    # Test network connectivity
    if ! test_network; then
        print_error "Network connectivity issues detected"
        print_status "Please check your internet connection and try again"
        exit 1
    fi
    
    # Try different installation methods
    INSTALL_METHODS=(
        "install_python3_pip_apt"
        "install_pip_get_pip"
        "install_pip_easy_install"
    )
    
    INSTALLED=false
    
    for method in "${INSTALL_METHODS[@]}"; do
        print_status "Trying installation method: $method"
        
        if $method; then
            print_success "Installation successful with method: $method"
            INSTALLED=true
            break
        else
            print_warning "Installation failed with method: $method"
        fi
        
        echo ""
    done
    
    if [ "$INSTALLED" = false ]; then
        print_error "All installation methods failed"
        print_status "Please try manual installation:"
        print_status "1. sudo apt-get update && sudo apt-get install python3-pip"
        print_status "2. curl -L https://bootstrap.pypa.io/get-pip.py | python3"
        exit 1
    fi
    
    echo ""
    
    # Verify installation
    if verify_pip_installation; then
        print_success "pip installation verified successfully"
    else
        print_warning "pip installation verification failed"
    fi
    
    echo ""
    
    # Test functionality
    if test_pip_functionality; then
        print_success "pip functionality test passed!"
    else
        print_warning "pip functionality test failed"
    fi
    
    echo ""
    print_status "=== Installation Summary ==="
    print_success "python3-pip installation completed!"
    print_status "You can now use pip to install Python packages."
    print_status ""
    print_status "Common pip commands:"
    print_status "  pip3 install package_name"
    print_status "  pip3 install --user package_name"
    print_status "  pip3 list"
    print_status "  pip3 --version"
}

# Run the installation
main "$@" 