#!/bin/bash

# Complete Docker Setup Script for DSSAT + Python Environment
# DSSAT + Python环境的完整Docker设置脚本

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

# Function to show banner
show_banner() {
    echo "================================================================"
    echo "            DSSAT + Python Complete Docker Setup"
    echo "            DSSAT + Python完整Docker设置"
    echo "================================================================"
    echo ""
    echo "This script will:"
    echo "此脚本将："
    echo "1. Check system requirements / 检查系统要求"
    echo "2. Make scripts executable / 使脚本可执行"
    echo "3. Build Docker image with DSSAT + Python / 构建包含DSSAT + Python的Docker镜像"
    echo "4. Test the installation / 测试安装"
    echo "5. Show usage instructions / 显示使用说明"
    echo ""
    echo "================================================================"
    echo ""
}

# Function to check system requirements
check_system_requirements() {
    print_status "Checking system requirements..."
    print_status "检查系统要求..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        print_error "Docker未安装！"
        echo ""
        print_status "Please install Docker first:"
        print_status "请先安装Docker："
        echo "  - Windows: Download Docker Desktop from https://docker.com"
        echo "  - macOS: Download Docker Desktop from https://docker.com"
        echo "  - Linux: sudo apt-get install docker.io (Ubuntu/Debian)"
        echo ""
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running!"
        print_error "Docker未运行！"
        print_status "Please start Docker and try again."
        print_status "请启动Docker后重试。"
        exit 1
    fi
    
    # Check available disk space (approximate)
    if command -v df &> /dev/null; then
        local available_space=$(df . | tail -1 | awk '{print $4}')
        local space_gb=$((available_space / 1024 / 1024))
        if [ $space_gb -lt 5 ]; then
            print_warning "Low disk space detected (${space_gb}GB available)"
            print_warning "检测到磁盘空间不足（可用${space_gb}GB）"
            print_warning "Docker image may require 3-5GB of space."
            print_warning "Docker镜像可能需要3-5GB空间。"
            echo ""
        fi
    fi
    
    print_success "System requirements check passed!"
    print_success "系统要求检查通过！"
}

# Function to check required files
check_required_files() {
    print_status "Checking required files..."
    print_status "检查必需文件..."
    
    local missing_files=()
    
    # Check for main Docker files
    if [ ! -f "Dockerfile.comprehensive" ]; then
        missing_files+=("Dockerfile.comprehensive")
    fi
    
    if [ ! -f "docker_build.sh" ]; then
        missing_files+=("docker_build.sh")
    fi
    
    if [ ! -f "docker_run.sh" ]; then
        missing_files+=("docker_run.sh")
    fi
    
    # Check for source directories
    if [ ! -d "dssat-csm-os-develop" ]; then
        missing_files+=("dssat-csm-os-develop/ (DSSAT source code)")
    fi
    
    if [ ! -d "dssat-csm-data-develop" ]; then
        missing_files+=("dssat-csm-data-develop/ (DSSAT data files)")
    fi
    
    # Check for Python files
    if [ ! -f "requirements.txt" ]; then
        missing_files+=("requirements.txt")
    fi
    
    if [ ! -f "cropgro-strawberry-implementation.py" ]; then
        missing_files+=("cropgro-strawberry-implementation.py")
    fi
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        print_error "Missing required files/directories:"
        print_error "缺少必需的文件/目录："
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        echo ""
        print_error "Please ensure you're running this script from the CN-strawberryDSSAT project root directory."
        print_error "请确保您在CN-strawberryDSSAT项目根目录中运行此脚本。"
        exit 1
    fi
    
    print_success "All required files found!"
    print_success "找到所有必需文件！"
}

# Function to make scripts executable
make_scripts_executable() {
    print_status "Making scripts executable..."
    print_status "使脚本可执行..."
    
    chmod +x docker_build.sh 2>/dev/null || true
    chmod +x docker_run.sh 2>/dev/null || true
    chmod +x docker_setup_complete.sh 2>/dev/null || true
    
    print_success "Scripts are now executable!"
    print_success "脚本现在可执行！"
}

# Function to build Docker image
build_docker_image() {
    print_status "Building Docker image..."
    print_status "构建Docker镜像..."
    print_warning "This will take 10-20 minutes depending on your internet connection."
    print_warning "这将需要10-20分钟，取决于您的网络连接速度。"
    echo ""
    
    if ./docker_build.sh; then
        print_success "Docker image built successfully!"
        print_success "Docker镜像构建成功！"
    else
        print_error "Docker build failed!"
        print_error "Docker构建失败！"
        print_status "Check the error messages above and docker_build.log for details."
        print_status "查看上面的错误信息和docker_build.log文件了解详情。"
        exit 1
    fi
}

# Function to test installation
test_installation() {
    print_status "Testing installation..."
    print_status "测试安装..."
    
    # Test if container runs
    if ./docker_run.sh --container-help > /dev/null 2>&1; then
        print_success "Installation test passed!"
        print_success "安装测试通过！"
    else
        print_warning "Installation test had issues, but setup completed."
        print_warning "安装测试有问题，但设置已完成。"
    fi
}

# Function to show final instructions
show_final_instructions() {
    echo ""
    echo "================================================================"
    print_success "Setup completed successfully!"
    print_success "设置成功完成！"
    echo "================================================================"
    echo ""
    
    print_status "Quick Start Guide / 快速开始指南:"
    echo ""
    echo "1. Interactive Shell / 交互式Shell:"
    echo "   ./docker_run.sh"
    echo ""
    echo "2. Run Python Model / 运行Python模型:"
    echo "   ./docker_run.sh --python-model"
    echo ""
    echo "3. Run Python Tests / 运行Python测试:"
    echo "   ./docker_run.sh --python-tests"
    echo ""
    echo "4. Start Jupyter Notebook / 启动Jupyter Notebook:"
    echo "   ./docker_run.sh --jupyter"
    echo "   Then open: http://localhost:8888"
    echo ""
    echo "5. Run DSSAT Batch Experiments / 运行DSSAT批量实验:"
    echo "   ./docker_run.sh --dssat-batch"
    echo ""
    echo "6. Run Single DSSAT Experiment / 运行单个DSSAT实验:"
    echo "   ./docker_run.sh --dssat-single UFBA1601.SRX"
    echo ""
    echo "7. Compare Models / 对比模型:"
    echo "   ./docker_run.sh --compare /app/dssat/Strawberry/UFBA1601.SRX"
    echo ""
    echo "8. Validate Models / 验证模型:"
    echo "   ./docker_run.sh --validate /app/dssat/Strawberry/UFBA1601.SRX"
    echo ""
    echo "9. Get Container Help / 获取容器帮助:"
    echo "   ./docker_run.sh --container-help"
    echo ""
    echo "10. Full Help / 完整帮助:"
    echo "    ./docker_run.sh --help"
    echo ""
    echo "================================================================"
    echo ""
    print_status "Files in your project directory will be available at /app/host-data inside the container."
    print_status "项目目录中的文件在容器内的 /app/host-data 路径下可用。"
    echo ""
    print_warning "Remember: All changes inside the container (except in /app/host-data) will be lost when the container stops."
    print_warning "记住：容器内的所有更改（除了 /app/host-data）在容器停止时都会丢失。"
    echo ""
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "用法: $0 [选项]"
    echo ""
    echo "Options:"
    echo "选项："
    echo "  --build-only      Only build Docker image, don't test"
    echo "                    仅构建Docker镜像，不测试"
    echo "  --test-only       Only test existing installation"
    echo "                    仅测试现有安装"
    echo "  --help            Show this help message"
    echo "                    显示此帮助信息"
    echo ""
    echo "Examples:"
    echo "示例："
    echo "  $0                # Full setup"
    echo "                    # 完整设置"
    echo "  $0 --build-only   # Build only"
    echo "                    # 仅构建"
    echo "  $0 --test-only    # Test only"
    echo "                    # 仅测试"
}

# Main function
main() {
    # Parse command line arguments
    local build_only=false
    local test_only=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build-only)
                build_only=true
                shift
                ;;
            --test-only)
                test_only=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Show banner
    show_banner
    
    # Check system requirements
    check_system_requirements
    
    # Check required files
    check_required_files
    
    # Make scripts executable
    make_scripts_executable
    
    if [ "$test_only" = true ]; then
        test_installation
        show_final_instructions
        exit 0
    fi
    
    # Build Docker image
    build_docker_image
    
    if [ "$build_only" = false ]; then
        # Test installation
        test_installation
    fi
    
    # Show final instructions
    show_final_instructions
}

# Run main function
main "$@"