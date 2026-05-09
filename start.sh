#!/bin/bash

# LangGraph 多智能体助手 - 一键启动脚本

echo "🚀 启动 LangGraph 多智能体助手..."
echo "================================"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查是否安装了 concurrently
if ! command -v concurrently &> /dev/null; then
    echo "📦 安装 concurrently..."
    npm install -g concurrently 2>/dev/null || sudo npm install -g concurrently
fi

# 启动后端和前端
echo ""
echo "📡 后端地址: http://localhost:8000"
echo "🌐 前端地址: http://localhost:3000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "================================"
echo ""

# 使用 concurrently 并行运行
concurrently -n "后端,前端" -c "blue,green" \
    "python main.py" \
    "cd frontend && npm run dev"
