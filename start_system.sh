#!/bin/bash

# 脑机接口系统启动脚本
# 用于启动Python服务端

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
CONFIG_FILE="$SERVER_DIR/config/settings.yaml"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未找到，请先安装Python 3.8或更高版本"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    log_info "Python版本: $python_version"
    
    # 检查Python版本是否满足要求
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_info "Python版本满足要求"
    else
        log_error "需要Python 3.8或更高版本"
        exit 1
    fi
}

# 检查依赖包
check_dependencies() {
    log_info "检查Python依赖包..."
    
    cd "$SERVER_DIR"
    
    # 尝试安装依赖
    if [ -f "requirements.txt" ]; then
        log_info "安装依赖包..."
        pip3 install -r requirements.txt
        if [ $? -eq 0 ]; then
            log_info "依赖包安装成功"
        else
            log_warn "依赖包安装可能有问题，继续运行..."
        fi
    else
        log_warn "requirements.txt 文件未找到"
    fi
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "配置文件未找到: $CONFIG_FILE"
        exit 1
    fi
    
    # 验证YAML文件格式
    if python3 -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>/dev/null; then
        log_info "配置文件格式正确"
    else
        log_error "配置文件格式错误"
        exit 1
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    # 创建日志目录
    mkdir -p "$SERVER_DIR/logs"
    
    # 创建数据目录
    mkdir -p "$SERVER_DIR/data"
    
    log_info "目录创建完成"
}

# 检查端口占用
check_ports() {
    log_info "检查端口占用情况..."
    
    # 从配置文件中读取端口
    if [ -f "$CONFIG_FILE" ]; then
        server_port=$(python3 -c "
import yaml
config = yaml.safe_load(open('$CONFIG_FILE'))
print(config.get('communication', {}).get('udp', {}).get('server_port', 9999))
" 2>/dev/null)
        
        if [ ! -z "$server_port" ]; then
            if netstat -tuln 2>/dev/null | grep -q ":$server_port "; then
                log_warn "端口 $server_port 已被占用"
                log_warn "可能已经有实例在运行"
            else
                log_info "端口 $server_port 可用"
            fi
        fi
    fi
}

# 启动系统
start_system() {
    log_info "启动脑机接口系统..."
    
    cd "$SERVER_DIR"
    
    # 检查是否在后台运行
    if [ "$1" = "background" ]; then
        log_info "在后台启动系统..."
        nohup python3 main.py > ../logs/console.log 2>&1 &
        echo $! > ../logs/system.pid
        log_info "系统已在后台启动，PID: $(cat ../logs/system.pid)"
        log_info "日志文件: ../logs/console.log"
    else
        log_info "在前台启动系统..."
        log_info "按 Ctrl+C 停止系统"
        python3 main.py
    fi
}

# 停止系统
stop_system() {
    log_info "停止脑机接口系统..."
    
    pid_file="$SCRIPT_DIR/logs/system.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "停止进程 PID: $pid"
            kill "$pid"
            sleep 2
            
            # 强制停止
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "强制停止进程"
                kill -9 "$pid"
            fi
            
            rm "$pid_file"
            log_info "系统已停止"
        else
            log_warn "进程 $pid 不存在"
            rm "$pid_file"
        fi
    else
        # 尝试查找并停止进程
        pkill -f "python.*main.py"
        if [ $? -eq 0 ]; then
            log_info "已停止所有相关进程"
        else
            log_warn "未找到运行中的系统进程"
        fi
    fi
}

# 检查系统状态
check_status() {
    log_info "检查系统状态..."
    
    pid_file="$SCRIPT_DIR/logs/system.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "系统运行中，PID: $pid"
            
            # 显示系统资源使用情况
            if command -v ps &> /dev/null; then
                ps -p "$pid" -o pid,pcpu,pmem,cmd
            fi
        else
            log_warn "系统未运行（PID文件存在但进程不存在）"
            rm "$pid_file"
        fi
    else
        log_info "系统未运行"
        
        # 尝试查找相关进程
        if pgrep -f "python.*main.py" > /dev/null; then
            log_warn "发现相关进程但PID文件不存在"
            pids=$(pgrep -f "python.*main.py")
            for pid in $pids; do
                log_info "进程 PID: $pid"
            done
        fi
    fi
}

# 显示帮助信息
show_help() {
    echo "脑机接口系统启动脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start      启动系统（前台）"
    echo "  start-bg   启动系统（后台）"
    echo "  stop       停止系统"
    echo "  restart    重启系统"
    echo "  status     检查系统状态"
    echo "  check      检查系统环境"
    echo "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start       # 前台启动"
    echo "  $0 start-bg    # 后台启动"
    echo "  $0 stop        # 停止系统"
    echo "  $0 restart     # 重启系统"
    echo ""
}

# 检查系统环境
check_environment() {
    log_info "检查系统环境..."
    
    check_python
    check_dependencies
    check_config
    create_directories
    check_ports
    
    log_info "环境检查完成"
}

# 重启系统
restart_system() {
    log_info "重启系统..."
    stop_system
    sleep 2
    start_system "background"
}

# 主逻辑
main() {
    case "${1:-help}" in
        "start")
            check_environment
            start_system
            ;;
        "start-bg")
            check_environment
            start_system "background"
            ;;
        "stop")
            stop_system
            ;;
        "restart")
            restart_system
            ;;
        "status")
            check_status
            ;;
        "check")
            check_environment
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# 信号处理
trap 'log_info "接收到中断信号，正在停止..."; stop_system; exit 0' INT TERM

# 执行主逻辑
main "$@"