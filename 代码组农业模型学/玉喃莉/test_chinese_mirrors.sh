#!/usr/bin/env bash

# 国内镜像测试脚本 / Chinese Mirror Test Script
# 测试各种国内镜像源的连接性和速度

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

# Function to test mirror connectivity and speed
test_mirror() {
    local mirror_url="$1"
    local mirror_name="$2"
    local mirror_type="$3"
    
    print_status "Testing $mirror_type mirror: $mirror_name"
    
    # Test connectivity
    if curl -s --connect-timeout 5 --max-time 10 "$mirror_url" >/dev/null 2>&1; then
        print_success "✅ $mirror_name is accessible"
        
        # Test speed (simple ping test)
        local start_time=$(date +%s%N)
        if curl -s --connect-timeout 3 --max-time 5 "$mirror_url" >/dev/null 2>&1; then
            local end_time=$(date +%s%N)
            local duration=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
            print_status "   Speed: ${duration}ms"
            echo "$mirror_name|$mirror_url|$duration" >> /tmp/mirror_results.txt
        else
            print_warning "   Speed test failed"
            echo "$mirror_name|$mirror_url|9999" >> /tmp/mirror_results.txt
        fi
        return 0
    else
        print_error "❌ $mirror_name is not accessible"
        echo "$mirror_name|$mirror_url|9999" >> /tmp/mirror_results.txt
        return 1
    fi
}

# Function to test pip mirrors
test_pip_mirrors() {
    print_status "=== Testing PyPI Mirrors ==="
    
    # Clear results file
    > /tmp/mirror_results.txt
    
    # Define pip mirrors
    PIP_MIRRORS=(
        "https://pypi.tuna.tsinghua.edu.cn/simple/|清华大学镜像源"
        "https://mirrors.aliyun.com/pypi/simple/|阿里云镜像源"
        "https://pypi.douban.com/simple/|豆瓣镜像源"
        "https://pypi.mirrors.ustc.edu.cn/simple/|中科大镜像源"
        "https://pypi.hustunique.com/simple/|华中科技大学镜像源"
        "https://pypi.sdutlinux.org/simple/|山东理工大学镜像源"
        "https://pypi.org/simple/|官方PyPI源"
    )
    
    for mirror_info in "${PIP_MIRRORS[@]}"; do
        IFS='|' read -r mirror_url mirror_name <<< "$mirror_info"
        test_mirror "$mirror_url" "$mirror_name" "PyPI"
    done
    
    # Show results
    print_status "=== PyPI Mirror Results ==="
    if [[ -f /tmp/mirror_results.txt ]]; then
        sort -t'|' -k3 -n /tmp/mirror_results.txt | while IFS='|' read -r name url speed; do
            if [[ "$speed" == "9999" ]]; then
                print_error "❌ $name - Not accessible"
            else
                print_success "✅ $name - ${speed}ms"
            fi
        done
    fi
}

# Function to test apt mirrors
test_apt_mirrors() {
    print_status "=== Testing APT Mirrors ==="
    
    # Clear results file
    > /tmp/mirror_results.txt
    
    # Detect OS
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        OS_NAME="$ID"
        OS_VERSION="$VERSION_ID"
        print_status "Detected: $OS_NAME $OS_VERSION"
    else
        print_warning "Cannot detect OS, skipping apt mirror test"
        return
    fi
    
    # Define apt mirrors based on OS
    case "$OS_NAME" in
        "ubuntu")
            APT_MIRRORS=(
                "https://mirrors.tuna.tsinghua.edu.cn/ubuntu/|清华大学镜像源"
                "https://mirrors.aliyun.com/ubuntu/|阿里云镜像源"
                "https://mirrors.ustc.edu.cn/ubuntu/|中科大镜像源"
                "https://mirrors.huaweicloud.com/ubuntu/|华为云镜像源"
                "http://archive.ubuntu.com/ubuntu/|官方Ubuntu源"
            )
            ;;
        "debian")
            APT_MIRRORS=(
                "https://mirrors.tuna.tsinghua.edu.cn/debian/|清华大学镜像源"
                "https://mirrors.aliyun.com/debian/|阿里云镜像源"
                "https://mirrors.ustc.edu.cn/debian/|中科大镜像源"
                "https://mirrors.huaweicloud.com/debian/|华为云镜像源"
                "http://deb.debian.org/debian/|官方Debian源"
            )
            ;;
        *)
            print_warning "Unsupported OS: $OS_NAME, skipping apt mirror test"
            return
            ;;
    esac
    
    for mirror_info in "${APT_MIRRORS[@]}"; do
        IFS='|' read -r mirror_url mirror_name <<< "$mirror_info"
        test_mirror "$mirror_url" "$mirror_name" "APT"
    done
    
    # Show results
    print_status "=== APT Mirror Results ==="
    if [[ -f /tmp/mirror_results.txt ]]; then
        sort -t'|' -k3 -n /tmp/mirror_results.txt | while IFS='|' read -r name url speed; do
            if [[ "$speed" == "9999" ]]; then
                print_error "❌ $name - Not accessible"
            else
                print_success "✅ $name - ${speed}ms"
            fi
        done
    fi
}

# Function to test yum/dnf mirrors
test_yum_mirrors() {
    print_status "=== Testing YUM/DNF Mirrors ==="
    
    # Clear results file
    > /tmp/mirror_results.txt
    
    # Check if yum or dnf is available
    if command_exists dnf; then
        PACKAGE_MANAGER="dnf"
    elif command_exists yum; then
        PACKAGE_MANAGER="yum"
    else
        print_warning "Neither yum nor dnf found, skipping yum mirror test"
        return
    fi
    
    print_status "Using $PACKAGE_MANAGER package manager"
    
    # Define yum/dnf mirrors
    YUM_MIRRORS=(
        "https://mirrors.tuna.tsinghua.edu.cn/centos/|清华大学镜像源"
        "https://mirrors.aliyun.com/centos/|阿里云镜像源"
        "https://mirrors.ustc.edu.cn/centos/|中科大镜像源"
        "https://mirrors.huaweicloud.com/centos/|华为云镜像源"
        "http://mirror.centos.org/centos/|官方CentOS源"
    )
    
    for mirror_info in "${YUM_MIRRORS[@]}"; do
        IFS='|' read -r mirror_url mirror_name <<< "$mirror_info"
        test_mirror "$mirror_url" "$mirror_name" "YUM/DNF"
    done
    
    # Show results
    print_status "=== YUM/DNF Mirror Results ==="
    if [[ -f /tmp/mirror_results.txt ]]; then
        sort -t'|' -k3 -n /tmp/mirror_results.txt | while IFS='|' read -r name url speed; do
            if [[ "$speed" == "9999" ]]; then
                print_error "❌ $name - Not accessible"
            else
                print_success "✅ $name - ${speed}ms"
            fi
        done
    fi
}

# Function to show current mirror configuration
show_current_config() {
    print_status "=== Current Mirror Configuration ==="
    
    # Show pip configuration
    print_status "Pip configuration:"
    if [[ -f ~/.pip/pip.conf ]]; then
        print_success "~/.pip/pip.conf exists"
        grep "index-url" ~/.pip/pip.conf 2>/dev/null || print_warning "No index-url found"
    else
        print_warning "~/.pip/pip.conf not found"
    fi
    
    if [[ -f ~/.config/pip/pip.conf ]]; then
        print_success "~/.config/pip/pip.conf exists"
        grep "index-url" ~/.config/pip/pip.conf 2>/dev/null || print_warning "No index-url found"
    else
        print_warning "~/.config/pip/pip.conf not found"
    fi
    
    # Show apt configuration
    print_status "APT configuration:"
    if [[ -f /etc/apt/sources.list ]]; then
        print_success "/etc/apt/sources.list exists"
        head -3 /etc/apt/sources.list | while read line; do
            if [[ "$line" =~ ^# ]]; then
                print_status "  $line"
            else
                print_status "  $line"
            fi
        done
    else
        print_warning "/etc/apt/sources.list not found"
    fi
    
    # Show yum configuration
    print_status "YUM/DNF configuration:"
    if [[ -f /etc/yum.repos.d/CentOS-Base.repo ]]; then
        print_success "/etc/yum.repos.d/CentOS-Base.repo exists"
        grep "baseurl" /etc/yum.repos.d/CentOS-Base.repo | head -1 | while read line; do
            print_status "  $line"
        done
    else
        print_warning "/etc/yum.repos.d/CentOS-Base.repo not found"
    fi
}

# Main function
main() {
    print_status "Starting Chinese mirror connectivity and speed test..."
    print_status "开始测试国内镜像源连接性和速度..."
    echo ""
    
    # Show current configuration
    show_current_config
    echo ""
    
    # Test all mirror types
    test_pip_mirrors
    echo ""
    
    test_apt_mirrors
    echo ""
    
    test_yum_mirrors
    echo ""
    
    # Clean up
    rm -f /tmp/mirror_results.txt
    
    print_status "=== Test Summary ==="
    print_status "测试完成！建议使用响应最快的镜像源。"
    print_status "Test completed! It's recommended to use the fastest responding mirror."
    print_status ""
    print_status "To configure mirrors automatically, run:"
    print_status "要自动配置镜像源，请运行："
    print_status "  ./setup_windows5.sh"
}

# Run the test
main "$@" 