#!/bin/bash

# LangGraph 多智能体助手 - 一键启动脚本（支持 Python 虚拟环境）

echo "🚀 启动 LangGraph 多智能体助手..."
echo "================================"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 虚拟环境目录
VENV_DIR="$SCRIPT_DIR/venv"

# ======================
# 检查 Python 是否安装
# ======================
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3"
    exit 1
fi

echo "📋 Python 版本: $(python3 --version)"

# ======================
# 检查并创建虚拟环境
# ======================
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "📦 创建 Python 虚拟环境..."
    rm -rf "$VENV_DIR"  # 清理可能损坏的虚拟环境
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "❌ 创建虚拟环境失败，请确保已安装 python3-venv"
        echo "   macOS: brew install python3 (已包含 venv)"
        echo "   Ubuntu/Debian: sudo apt install python3-venv"
        echo "   CentOS/RHEL: sudo yum install python3-virtualenv"
        exit 1
    fi
    
    # 验证虚拟环境是否创建成功
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo "❌ 虚拟环境创建失败，activate 文件不存在"
        exit 1
    fi
    
    # 配置 pip 国内镜像源（加速下载）
    echo "⚙️  配置 pip 清华镜像源..."
    mkdir -p "$VENV_DIR"
    cat > "$VENV_DIR/pip.conf" << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
    
    echo "✅ 虚拟环境创建成功"
fi

# ======================
# 激活虚拟环境
# ======================
echo "🔧 激活虚拟环境..."
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    echo "❌ 激活虚拟环境失败"
    exit 1
fi

# ======================
# 检查并安装依赖
# ======================
if [ ! -f "$VENV_DIR/.dependencies_installed" ] || [ "$SCRIPT_DIR/requirements.txt" -nt "$VENV_DIR/.dependencies_installed" ]; then
    echo "📥 安装 Python 依赖..."
    pip install --upgrade pip
    if [ $? -ne 0 ]; then
        echo "❌ pip 升级失败"
        exit 1
    fi
    
    pip install -r "$SCRIPT_DIR/requirements.txt"
    if [ $? -eq 0 ]; then
        touch "$VENV_DIR/.dependencies_installed"
        echo "✅ 依赖安装完成"
    else
        echo "❌ 依赖安装失败"
        exit 1
    fi
else
    echo "✅ 依赖已安装且为最新"
fi

# ======================
# 检查 .env 文件
# ======================
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚠️  未找到 .env 文件，请确保已配置环境变量"
    echo "   可以复制 .env.example 并修改："
    echo "   cp .env.example .env"
fi

# ======================
# 检查是否安装了 concurrently
# ======================
if ! command -v concurrently &> /dev/null; then
    echo "📦 安装 concurrently..."
    npm install -g concurrently 2>/dev/null || sudo npm install -g concurrently 2>/dev/null
fi

# ======================
# 启动服务
# ======================
echo ""
echo "📡 后端地址: http://localhost:8000"
echo "🌐 前端地址: http://localhost:3000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "================================"
echo ""

# 使用虚拟环境中的 Python 启动后端
concurrently -n "后端,前端" -c "blue,green" \
    "$VENV_DIR/bin/python main.py" \
    "cd frontend && npm run dev"
