#!/bin/bash

# Comprehensive DSSAT + Python Docker Build Script
# 综合DSSAT + Python Docker构建脚本

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

# Check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        print_error "Docker未安装。请先安装Docker。"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        print_error "Docker未运行。请先启动Docker。"
        exit 1
    fi

    print_success "Docker is available and running."
}

# Function to check required files
check_required_files() {
    print_status "Checking required files..."
    
    local missing_files=()
    
    if [ ! -f "Dockerfile.comprehensive" ]; then
        missing_files+=("Dockerfile.comprehensive")
    fi
    
    if [ ! -d "dssat-csm-os-develop" ]; then
        missing_files+=("dssat-csm-os-develop/")
    fi
    
    if [ ! -d "dssat-csm-data-develop" ]; then
        missing_files+=("dssat-csm-data-develop/")
    fi
    
    if [ ! -f "requirements.txt" ]; then
        missing_files+=("requirements.txt")
    fi
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        print_error "Missing required files/directories:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        print_error "Please ensure you're running this script from the CN-strawberryDSSAT project root directory."
        exit 1
    fi
    
    print_success "All required files found."
}

# Function to clean old Docker images
clean_old_images() {
    print_status "Cleaning old Docker images..."
    
    # Remove old strawberry-dssat images
    OLD_IMAGES=$(docker images -q strawberry-dssat 2>/dev/null)
    if [ ! -z "$OLD_IMAGES" ]; then
        print_warning "Removing old strawberry-dssat images..."
        docker rmi $OLD_IMAGES 2>/dev/null || true
    fi
    
    # Clean up dangling images
    DANGLING_IMAGES=$(docker images -f "dangling=true" -q 2>/dev/null)
    if [ ! -z "$DANGLING_IMAGES" ]; then
        print_warning "Removing dangling images..."
        docker rmi $DANGLING_IMAGES 2>/dev/null || true
    fi
    
    print_success "Docker cleanup completed."
}

# Function to build Docker image
build_image() {
    local image_name="strawberry-dssat:latest"
    local dockerfile="Dockerfile.comprehensive"
    
    print_status "Building comprehensive DSSAT + Python Docker image..."
    print_status "构建综合DSSAT + Python Docker镜像..."
    print_warning "This may take 10-20 minutes depending on your internet connection."
    print_warning "这可能需要10-20分钟，取决于您的网络连接。"
    echo ""
    
    # Build with detailed output
    if docker build \
        --tag "$image_name" \
        --file "$dockerfile" \
        --progress=plain \
        --no-cache \
        . 2>&1 | tee docker_build.log; then
        
        print_success "Docker image built successfully!"
        print_success "Docker镜像构建成功！"
        print_status "Image name: $image_name"
        print_status "镜像名称: $image_name"
        
        # Show image size
        local image_size=$(docker images strawberry-dssat:latest --format "table {{.Size}}" | tail -n 1)
        print_status "Image size: $image_size"
        print_status "镜像大小: $image_size"
        
    else
        print_error "Docker build failed!"
        print_error "Docker构建失败！"
        print_error "Check docker_build.log for details."
        print_error "查看docker_build.log文件了解详情。"
        exit 1
    fi
}

# Function to test the built image
test_image() {
    print_status "Testing the built Docker image..."
    
    # Test if the image runs
    if docker run --rm strawberry-dssat:latest /app/help.sh > /dev/null 2>&1; then
        print_success "Docker image test passed!"
        print_success "Docker镜像测试通过！"
    else
        print_warning "Docker image test failed, but image was built."
        print_warning "Docker镜像测试失败，但镜像已构建。"
    fi
}

# Function to show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "用法: $0 [选项]"
    echo ""
    echo "Options:"
    echo "选项："
    echo "  --clean-only    Only clean old Docker images, don't build"
    echo "                  仅清理旧Docker镜像，不构建"
    echo "  --no-clean      Skip cleaning old images before build"
    echo "                  构建前跳过清理旧镜像"
    echo "  --help          Show this help message"
    echo "                  显示此帮助信息"
    echo ""
    echo "Examples:"
    echo "示例："
    echo "  $0              # Full build with cleanup"
    echo "                  # 完整构建包括清理"
    echo "  $0 --no-clean   # Build without cleanup"
    echo "                  # 构建不包括清理"
    echo "  $0 --clean-only # Only cleanup"
    echo "                  # 仅清理"
}

# Main function
main() {
    echo "============================================"
    echo "DSSAT + Python Docker Build Script"
    echo "DSSAT + Python Docker构建脚本"
    echo "============================================"
    echo ""
    
    # Parse command line arguments
    local clean_only=false
    local no_clean=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean-only)
                clean_only=true
                shift
                ;;
            --no-clean)
                no_clean=true
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
    
    # Check Docker
    check_docker
    
    # Clean old images if requested
    if [ "$clean_only" = true ]; then
        clean_old_images
        print_success "Cleanup completed. Exiting."
        exit 0
    fi
    
    # Check required files
    check_required_files
    
    # Clean old images unless --no-clean specified
    if [ "$no_clean" = false ]; then
        clean_old_images
    fi
    
    # Build the image
    build_image
    
    # Test the image
    test_image
    
    echo ""
    echo "============================================"
    print_success "Build process completed!"
    print_success "构建过程完成！"
    echo "============================================"
    echo ""
    print_status "Next steps / 下一步:"
    print_status "1. Run the container: ./docker_run.sh"
    print_status "   运行容器: ./docker_run.sh"
    print_status "2. Or run specific commands: ./docker_run.sh --help"
    print_status "   或运行特定命令: ./docker_run.sh --help"
    echo ""
}

# Run main function
main "$@"