#!/usr/bin/env bash

# 修复 python3-venv 安装问题的脚本
# Script to fix python3-venv installation issues

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

# Function to configure apt mirrors for better package availability
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
        print_warning "Cannot detect OS version, using default mirrors"
        return 1
    fi
    
    # Define reliable Chinese mirrors
    case "$OS_NAME" in
        "ubuntu")
            # Use Alibaba mirror as primary (usually most reliable)
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
    
    # Update sources.list with the mirror
    print_status "Updating sources.list with $MIRROR_NAME..."
    
    sudo tee /etc/apt/sources.list > /dev/null << EOF
# Updated by fix script with $MIRROR_NAME
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

# Function to install python3-venv with multiple fallback options
install_python_venv() {
    print_status "Installing python3-venv with enhanced error handling..."
    
    # First, try to update package lists
    print_status "Updating package lists..."
    for attempt in 1 2 3; do
        if sudo apt-get update; then
            print_success "Package lists updated successfully"
            break
        else
            if [ $attempt -lt 3 ]; then
                print_warning "Package list update failed (attempt $attempt/3). Retrying..."
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
    
    # Try different package names for virtual environment support
    VENV_PACKAGES=(
        "python3-venv"
        "python3.10-venv"
        "python3.9-venv"
        "python3.8-venv"
        "python3.7-venv"
        "python3-virtualenv"
        "virtualenv"
    )
    
    print_status "Trying different virtual environment packages..."
    
    for package in "${VENV_PACKAGES[@]}"; do
        print_status "Checking availability of $package..."
        
        # Check if package is available
        if apt-cache search "$package" | grep -q "^$package "; then
            print_status "Package $package is available, attempting installation..."
            
            if sudo apt-get install -y "$package" python3-dev; then
                print_success "$package installed successfully"
                return 0
            else
                print_warning "Failed to install $package, trying next option..."
            fi
        else
            print_warning "Package $package is not available in repositories"
        fi
    done
    
    # If all packages failed, try alternative methods
    print_warning "All apt packages failed, trying alternative methods..."
    install_venv_alternative
}

# Function to install virtual environment using alternative methods
install_venv_alternative() {
    print_status "Installing virtual environment using alternative methods..."
    
    # Method 1: Install via pip
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    else
        print_error "No pip command available"
        return 1
    fi
    
    print_status "Installing virtualenv via pip..."
    
    # Try different mirrors
    MIRRORS=(
        "https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn"
        "https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
        "https://pypi.douban.com/simple/ --trusted-host pypi.douban.com"
    )
    
    for mirror in "${MIRRORS[@]}"; do
        print_status "Trying to install virtualenv using $(echo $mirror | cut -d' ' -f1)..."
        
        if sudo $PIP_CMD install -i $mirror virtualenv; then
            print_success "virtualenv installed successfully using $(echo $mirror | cut -d' ' -f1)"
            return 0
        else
            print_warning "Failed to install virtualenv using $(echo $mirror | cut -d' ' -f1)"
        fi
    done
    
    # Method 2: Try to download and install manually
    print_status "Trying to download virtualenv manually..."
    
    if command_exists curl; then
        DOWNLOAD_CMD="curl -L"
    elif command_exists wget; then
        DOWNLOAD_CMD="wget -O -"
    else
        print_error "Neither curl nor wget found"
        return 1
    fi
    
    # Download get-pip.py and install virtualenv
    if $DOWNLOAD_CMD https://bootstrap.pypa.io/get-pip.py > get-pip.py 2>/dev/null; then
        print_success "Downloaded get-pip.py"
        
        if python3 get-pip.py --user; then
            print_success "pip installed via get-pip.py"
            
            # Now try to install virtualenv
            if ~/.local/bin/pip install --user virtualenv; then
                print_success "virtualenv installed via user pip"
                export PATH="$HOME/.local/bin:$PATH"
                return 0
            fi
        fi
    fi
    
    print_error "All alternative methods failed"
    return 1
}

# Function to test virtual environment creation
test_venv_creation() {
    print_status "Testing virtual environment creation..."
    
    # Try different venv creation methods
    VENV_METHODS=(
        "python3 -m venv test_venv"
        "python3 -m virtualenv test_venv"
        "virtualenv test_venv"
        "~/.local/bin/virtualenv test_venv"
    )
    
    for method in "${VENV_METHODS[@]}"; do
        print_status "Trying: $method"
        
        if eval $method 2>/dev/null; then
            print_success "Virtual environment created successfully with: $method"
            
            # Test activation
            if source test_venv/bin/activate 2>/dev/null; then
                print_success "Virtual environment activation successful"
                deactivate 2>/dev/null
            else
                print_warning "Virtual environment activation failed"
            fi
            
            # Clean up
            rm -rf test_venv
            return 0
        else
            print_warning "Failed with: $method"
        fi
    done
    
    print_error "All virtual environment creation methods failed"
    return 1
}

# Main function
main() {
    print_status "Starting python3-venv installation fix..."
    echo ""
    
    # Check if we're on a supported system
    if ! command_exists apt-get; then
        print_error "This script is designed for Ubuntu/Debian systems"
        print_error "For other systems, please install virtual environment packages manually"
        exit 1
    fi
    
    # Check if python3 is available
    if ! command_exists python3; then
        print_error "python3 is not installed. Please install python3 first."
        exit 1
    fi
    
    print_status "Python3 version: $(python3 --version)"
    echo ""
    
    # Try to install python3-venv
    if install_python_venv; then
        print_success "python3-venv installation completed successfully"
    else
        print_warning "python3-venv installation had issues, but continuing..."
    fi
    
    echo ""
    
    # Test virtual environment creation
    if test_venv_creation; then
        print_success "Virtual environment creation test passed!"
    else
        print_warning "Virtual environment creation test failed"
        print_status "You may need to install virtual environment packages manually:"
        print_status "  sudo apt-get install python3-venv python3-dev"
        print_status "  sudo apt-get install python3-virtualenv"
        print_status "  pip install virtualenv"
    fi
    
    echo ""
    print_status "Fix completed. You can now try running the main setup script again."
}

# Run the fix
main "$@" 