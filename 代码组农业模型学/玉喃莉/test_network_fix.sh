#!/usr/bin/env bash

# Test script for network connectivity fixes
# 网络连接修复测试脚本

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
test_network_connectivity() {
    print_status "Testing network connectivity..."
    
    # Test basic internet connectivity
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        print_success "Basic internet connectivity: OK"
        return 0
    else
        print_warning "Basic internet connectivity: FAILED"
        return 1
    fi
}

# Function to fix network issues
fix_network_issues() {
    print_status "Attempting to fix network connectivity issues..."
    
    # Try to update DNS
    if command_exists systemctl; then
        print_status "Restarting network services..."
        sudo systemctl restart systemd-resolved 2>/dev/null || true
        sudo systemctl restart NetworkManager 2>/dev/null || true
    fi
    
    # Try to flush DNS cache
    if command_exists nscd; then
        print_status "Flushing DNS cache..."
        sudo nscd -i hosts 2>/dev/null || true
    fi
    
    # Wait a moment for network to stabilize
    sleep 3
    
    # Test again
    if test_network_connectivity; then
        print_success "Network connectivity restored!"
        return 0
    else
        print_warning "Network connectivity still problematic"
        return 1
    fi
}

# Function to test package manager with retry
test_package_manager() {
    print_status "Testing package manager functionality..."
    
    if command_exists apt-get; then
        print_status "Testing apt-get..."
        
        # Update package lists with retry mechanism
        for attempt in 1 2 3; do
            print_status "Updating package lists (attempt $attempt/3)..."
            if sudo apt-get update >/dev/null 2>&1; then
                print_success "Package list update successful on attempt $attempt"
                return 0
            else
                if [ $attempt -lt 3 ]; then
                    print_warning "Package list update failed. Retrying in 5 seconds..."
                    sleep 5
                else
                    print_error "Failed to update package lists after 3 attempts."
                    return 1
                fi
            fi
        done
    elif command_exists yum; then
        print_status "Testing yum..."
        if sudo yum check-update >/dev/null 2>&1; then
            print_success "yum check successful"
            return 0
        else
            print_error "yum check failed"
            return 1
        fi
    elif command_exists dnf; then
        print_status "Testing dnf..."
        if sudo dnf check-update >/dev/null 2>&1; then
            print_success "dnf check successful"
            return 0
        else
            print_error "dnf check failed"
            return 1
        fi
    else
        print_warning "No supported package manager found"
        return 1
    fi
}

# Main test function
main() {
    print_status "Starting network connectivity and package manager tests..."
    
    # Test 1: Network connectivity
    print_status "=== Test 1: Network Connectivity ==="
    if test_network_connectivity; then
        print_success "Network connectivity test passed!"
    else
        print_warning "Network connectivity test failed. Attempting to fix..."
        if fix_network_issues; then
            print_success "Network issues fixed!"
        else
            print_error "Network issues persist. Manual intervention may be required."
        fi
    fi
    
    # Test 2: Package manager functionality
    print_status "=== Test 2: Package Manager Functionality ==="
    if test_package_manager; then
        print_success "Package manager test passed!"
    else
        print_error "Package manager test failed. This may indicate network or configuration issues."
    fi
    
    # Test 3: Python availability
    print_status "=== Test 3: Python Availability ==="
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        print_success "Python 3 found: $PYTHON_VERSION"
    elif command_exists python; then
        PYTHON_VERSION=$(python --version 2>&1)
        print_success "Python found: $PYTHON_VERSION"
    else
        print_warning "Python not found. This is expected if not yet installed."
    fi
    
    # Test 4: pip availability
    print_status "=== Test 4: pip Availability ==="
    if command_exists pip3; then
        PIP_VERSION=$(pip3 --version 2>&1)
        print_success "pip3 found: $PIP_VERSION"
    elif command_exists pip; then
        PIP_VERSION=$(pip --version 2>&1)
        print_success "pip found: $PIP_VERSION"
    else
        print_warning "pip not found. This is expected if not yet installed."
    fi
    
    print_status "=== Test Summary ==="
    print_status "If all tests passed, you should be able to run the main setup script."
    print_status "If any tests failed, please check your internet connection and try again."
    print_status "For WSL users, ensure you're running this in a proper WSL environment."
}

# Run the test
main "$@" 