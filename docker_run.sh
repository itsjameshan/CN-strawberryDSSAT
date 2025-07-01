#!/bin/bash

# Comprehensive DSSAT + Python Docker Run Script
# 综合DSSAT + Python Docker运行脚本

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
}

# Check if image exists
check_image() {
    if ! docker images strawberry-dssat:latest --format "table {{.Repository}}" | grep -q strawberry-dssat; then
        print_error "Docker image 'strawberry-dssat:latest' not found!"
        print_error "未找到Docker镜像 'strawberry-dssat:latest'！"
        print_status "Please build the image first using: ./docker_build.sh"
        print_status "请先使用以下命令构建镜像: ./docker_build.sh"
        exit 1
    fi
}

# Function to run interactive shell
run_interactive() {
    local mount_data="${1:-true}"
    
    print_status "Starting interactive Docker container..."
    print_status "启动交互式Docker容器..."
    
    local docker_args=(
        "--rm"
        "--interactive"
        "--tty"
        "--name" "strawberry-dssat-interactive"
        "--hostname" "strawberry-dssat"
    )
    
    # Mount current directory if requested
    if [ "$mount_data" = true ]; then
        docker_args+=("--volume" "${PWD}:/app/host-data")
        print_status "Mounting current directory as /app/host-data"
        print_status "将当前目录挂载为 /app/host-data"
    fi
    
    print_status "Container will start with help information."
    print_status "容器将显示帮助信息。"
    print_warning "Type 'exit' to leave the container."
    print_warning "输入 'exit' 退出容器。"
    echo ""
    
    docker run "${docker_args[@]}" strawberry-dssat:latest /bin/bash -c "/app/help.sh; exec /bin/bash"
}

# Function to run Jupyter notebook
run_jupyter() {
    local port="${1:-8888}"
    
    print_status "Starting Jupyter notebook server on port $port..."
    print_status "在端口 $port 上启动Jupyter notebook服务器..."
    
    print_success "Jupyter will be available at: http://localhost:$port"
    print_success "Jupyter将在以下地址可用: http://localhost:$port"
    print_warning "Press Ctrl+C to stop the server."
    print_warning "按 Ctrl+C 停止服务器。"
    echo ""
    
    docker run \
        --rm \
        --interactive \
        --tty \
        --name "strawberry-dssat-jupyter" \
        --publish "$port:8888" \
        --volume "${PWD}:/app/host-data" \
        strawberry-dssat:latest \
        /app/start_jupyter.sh
}

# Function to run Python model
run_python_model() {
    print_status "Running Python strawberry model..."
    print_status "运行Python草莓模型..."
    
    docker run \
        --rm \
        --interactive \
        --tty \
        --volume "${PWD}:/app/host-data" \
        strawberry-dssat:latest \
        /app/run_python_model.sh "$@"
}

# Function to run Python tests
run_python_tests() {
    print_status "Running Python model tests..."
    print_status "运行Python模型测试..."
    
    docker run \
        --rm \
        --interactive \
        --tty \
        --volume "${PWD}:/app/host-data" \
        strawberry-dssat:latest \
        /app/run_python_tests.sh
}

# Function to run DSSAT batch
run_dssat_batch() {
    print_status "Running DSSAT batch experiments..."
    print_status "运行DSSAT批量实验..."
    
    docker run \
        --rm \
        --interactive \
        --tty \
        --volume "${PWD}:/app/host-data" \
        strawberry-dssat:latest \
        /app/run_dssat_batch.sh
}

# Function to run DSSAT single experiment
run_dssat_single() {
    local experiment_file="$1"
    
    if [ -z "$experiment_file" ]; then
        print_error "Please specify an experiment file (.SRX)"
        print_error "请指定实验文件 (.SRX)"
        print_status "Usage: $0 --dssat-single <experiment_file.SRX>"
        print_status "用法: $0 --dssat-single <experiment_file.SRX>"
        return 1
    fi
    
    print_status "Running DSSAT single experiment: $experiment_file"
    print_status "运行DSSAT单个实验: $experiment_file"
    
    docker run \
        --rm \
        --interactive \
        --tty \
        --volume "${PWD}:/app/host-data" \
        strawberry-dssat:latest \
        /app/run_dssat_single.sh "$experiment_file"
}

# Function to compare models
run_compare_models() {
    local experiment_file="$1"
    
    if [ -z "$experiment_file" ]; then
        print_error "Please specify an experiment file (.SRX)"
        print_error "请指定实验文件 (.SRX)"
        print_status "Usage: $0 --compare <experiment_file.SRX>"
        print_status "用法: $0 --compare <experiment_file.SRX>"
        return 1
    fi
    
    print_status "Comparing Python vs DSSAT models: $experiment_file"
    print_status "对比Python与DSSAT模型: $experiment_file"
    
    docker run \
        --rm \
        --interactive \
        --tty \
        --volume "${PWD}:/app/host-data" \
        strawberry-dssat:latest \
        /app/compare_models.sh "$experiment_file"
}

# Function to validate models
run_validate_models() {
    local experiment_file="$1"
    local tolerance="${2:-1.0}"
    
    if [ -z "$experiment_file" ]; then
        print_error "Please specify an experiment file (.SRX)"
        print_error "请指定实验文件 (.SRX)"
        print_status "Usage: $0 --validate <experiment_file.SRX> [tolerance]"
        print_status "用法: $0 --validate <experiment_file.SRX> [容差]"
        return 1
    fi
    
    print_status "Validating models: $experiment_file (tolerance: $tolerance)"
    print_status "验证模型: $experiment_file (容差: $tolerance)"
    
    docker run \
        --rm \
        --interactive \
        --tty \
        --volume "${PWD}:/app/host-data" \
        strawberry-dssat:latest \
        /app/validate_models.sh "$experiment_file" "$tolerance"
}

# Function to run custom command
run_custom_command() {
    print_status "Running custom command in container..."
    print_status "在容器中运行自定义命令..."
    
    docker run \
        --rm \
        --interactive \
        --tty \
        --volume "${PWD}:/app/host-data" \
        strawberry-dssat:latest \
        "$@"
}

# Function to show container help
show_container_help() {
    print_status "Showing container help information..."
    
    docker run \
        --rm \
        strawberry-dssat:latest \
        /app/help.sh
}

# Function to show usage information
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "Commands:"
    echo "命令："
    echo "  --interactive, -i         Start interactive shell (default)"
    echo "                            启动交互式shell（默认）"
    echo "  --jupyter [port]          Start Jupyter notebook server (default port: 8888)"
    echo "                            启动Jupyter notebook服务器（默认端口：8888）"
    echo "  --python-model           Run Python strawberry model"
    echo "                            运行Python草莓模型"
    echo "  --python-tests           Run Python model tests"
    echo "                            运行Python模型测试"
    echo "  --dssat-batch            Run DSSAT batch experiments"
    echo "                            运行DSSAT批量实验"
    echo "  --dssat-single <file>    Run single DSSAT experiment"
    echo "                            运行单个DSSAT实验"
    echo "  --compare <file>         Compare Python vs DSSAT models"
    echo "                            对比Python与DSSAT模型"
    echo "  --validate <file> [tol]  Validate model accuracy (default tolerance: 1.0)"
    echo "                            验证模型精度（默认容差：1.0）"
    echo "  --container-help         Show container help information"
    echo "                            显示容器帮助信息"
    echo "  --custom-cmd <cmd>       Run custom command in container"
    echo "                            在容器中运行自定义命令"
    echo "  --help                   Show this help message"
    echo "                            显示此帮助信息"
    echo ""
    echo "Options:"
    echo "选项："
    echo "  --no-mount               Don't mount current directory (interactive mode only)"
    echo "                            不挂载当前目录（仅交互模式）"
    echo ""
    echo "Examples:"
    echo "示例："
    echo "  $0                                    # Interactive shell"
    echo "                                        # 交互式shell"
    echo "  $0 --jupyter 9999                    # Jupyter on port 9999"
    echo "                                        # 端口9999上的Jupyter"
    echo "  $0 --python-model                    # Run Python model"
    echo "                                        # 运行Python模型"
    echo "  $0 --dssat-single UFBA1601.SRX      # Run DSSAT experiment"
    echo "                                        # 运行DSSAT实验"
    echo "  $0 --compare /app/dssat/Strawberry/UFBA1601.SRX  # Compare models"
    echo "                                                     # 对比模型"
    echo "  $0 --validate /app/dssat/Strawberry/UFBA1601.SRX 0.5  # Validate with tolerance 0.5"
    echo "                                                          # 容差0.5验证"
    echo "  $0 --custom-cmd 'ls -la /app'        # Custom command"
    echo "                                        # 自定义命令"
    echo ""
    echo "Note: Current directory will be mounted as /app/host-data in the container."
    echo "注意：当前目录将在容器中挂载为 /app/host-data。"
}

# Main function
main() {
    # Check Docker
    check_docker
    
    # Check if image exists
    check_image
    
    # Parse command line arguments
    local command="interactive"
    local mount_data=true
    
    if [ $# -eq 0 ]; then
        command="interactive"
    else
        case $1 in
            --interactive|-i)
                command="interactive"
                shift
                ;;
            --jupyter)
                command="jupyter"
                shift
                ;;
            --python-model)
                command="python-model"
                shift
                ;;
            --python-tests)
                command="python-tests"
                shift
                ;;
            --dssat-batch)
                command="dssat-batch"
                shift
                ;;
            --dssat-single)
                command="dssat-single"
                shift
                ;;
            --compare)
                command="compare"
                shift
                ;;
            --validate)
                command="validate"
                shift
                ;;
            --container-help)
                command="container-help"
                shift
                ;;
            --custom-cmd)
                command="custom-cmd"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown command: $1"
                show_usage
                exit 1
                ;;
        esac
    fi
    
    # Check for --no-mount option
    if [[ "$*" == *"--no-mount"* ]]; then
        mount_data=false
        set -- "${@/--no-mount/}"  # Remove --no-mount from arguments
    fi
    
    # Execute the command
    case $command in
        interactive)
            run_interactive "$mount_data"
            ;;
        jupyter)
            run_jupyter "$1"
            ;;
        python-model)
            run_python_model "$@"
            ;;
        python-tests)
            run_python_tests
            ;;
        dssat-batch)
            run_dssat_batch
            ;;
        dssat-single)
            run_dssat_single "$1"
            ;;
        compare)
            run_compare_models "$1"
            ;;
        validate)
            run_validate_models "$1" "$2"
            ;;
        container-help)
            show_container_help
            ;;
        custom-cmd)
            run_custom_command "$@"
            ;;
        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"