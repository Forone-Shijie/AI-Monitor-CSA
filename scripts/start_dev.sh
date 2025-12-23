#!/bin/bash
#
# CC-SOP Monitor 开发环境启动脚本
# 同时启动后端 API 和前端开发服务器
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Conda 环境
CONDA_ENV="cc-sop"
PYTHON="/home/sjzhang/miniconda3/envs/$CONDA_ENV/bin/python"

# PID 文件
BACKEND_PID_FILE="/tmp/cc-sop-backend.pid"
FRONTEND_PID_FILE="/tmp/cc-sop-frontend.pid"

# 清理函数
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"

    if [ -f "$BACKEND_PID_FILE" ]; then
        BACKEND_PID=$(cat "$BACKEND_PID_FILE")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill "$BACKEND_PID" 2>/dev/null || true
            echo -e "${GREEN}  ✓ 后端服务已停止 (PID: $BACKEND_PID)${NC}"
        fi
        rm -f "$BACKEND_PID_FILE"
    fi

    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            kill "$FRONTEND_PID" 2>/dev/null || true
            echo -e "${GREEN}  ✓ 前端服务已停止 (PID: $FRONTEND_PID)${NC}"
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi

    echo -e "${GREEN}服务已全部停止${NC}"
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM

# 显示横幅
show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║            CC-SOP Monitor 开发环境                           ║"
    echo "║     客舱乘务员姿态与操作规范监测系统                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查端口占用
check_ports() {
    echo -e "${YELLOW}检查端口占用...${NC}"

    if lsof -i:8000 >/dev/null 2>&1; then
        echo -e "${RED}  ✗ 端口 8000 已被占用${NC}"
        echo -e "  请先停止占用该端口的进程: lsof -i:8000"
        exit 1
    fi

    if lsof -i:5173 >/dev/null 2>&1; then
        echo -e "${RED}  ✗ 端口 5173 已被占用${NC}"
        echo -e "  请先停止占用该端口的进程: lsof -i:5173"
        exit 1
    fi

    echo -e "${GREEN}  ✓ 端口可用${NC}"
}

# 启动后端
start_backend() {
    echo -e "${YELLOW}启动后端 API 服务...${NC}"
    cd "$BACKEND_DIR"

    # 后台启动
    $PYTHON -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$BACKEND_PID_FILE"

    # 等待启动
    sleep 2

    # 健康检查
    for i in {1..10}; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            echo -e "${GREEN}  ✓ 后端服务已启动 (PID: $BACKEND_PID)${NC}"
            echo -e "    API: ${CYAN}http://localhost:8000${NC}"
            echo -e "    文档: ${CYAN}http://localhost:8000/docs${NC}"
            return 0
        fi
        sleep 1
    done

    echo -e "${RED}  ✗ 后端服务启动失败${NC}"
    exit 1
}

# 启动前端
start_frontend() {
    echo -e "${YELLOW}启动前端开发服务器...${NC}"
    cd "$FRONTEND_DIR"

    # 检查依赖
    if [ ! -d "node_modules" ]; then
        echo -e "  安装前端依赖..."
        npm install
    fi

    # 后台启动
    npm run dev &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE"

    # 等待启动
    sleep 3

    echo -e "${GREEN}  ✓ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"
    echo -e "    前端: ${CYAN}http://localhost:5173${NC}"
}

# 显示服务状态
show_status() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}开发环境已就绪!${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  前端地址: ${CYAN}http://localhost:5173${NC}"
    echo -e "  后端 API: ${CYAN}http://localhost:8000${NC}"
    echo -e "  API 文档: ${CYAN}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "  按 ${YELLOW}Ctrl+C${NC} 停止所有服务"
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
}

# 主函数
main() {
    show_banner
    check_ports
    start_backend
    start_frontend
    show_status

    # 保持脚本运行
    wait
}

# 执行
main "$@"
