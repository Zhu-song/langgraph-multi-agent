#!/bin/bash

# LangGraph 多智能体助手 - 环境初始化脚本
# 用于手动创建虚拟环境、安装/更新依赖

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"

# 显示帮助信息
show_help() {
    echo "LangGraph 多智能体助手 - 环境管理脚本"
    echo ""
    echo "用法: ./setup.sh [命令]"
    echo ""
    echo "命令:"
    echo "  init       创建虚拟环境并安装依赖（首次使用）"
    echo "  install    安装/更新依赖"
    echo "  clean      删除虚拟环境"
    echo "  reset      重置虚拟环境（删除后重新创建）"
    echo "  shell      进入虚拟环境 Shell"
    echo "  help       显示此帮助信息"
    echo ""
}

# 创建虚拟环境
init_venv() {
    echo "📦 创建 Python 虚拟环境..."
    
    if [ -d "$VENV_DIR" ]; then
        echo "⚠️  虚拟环境已存在，跳过创建"
    else
        python3 -m venv "$VENV_DIR"
        echo "✅ 虚拟环境创建成功: $VENV_DIR"
    fi
    
    install_deps
}

# 安装依赖
install_deps() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "❌ 虚拟环境不存在，请先运行: ./setup.sh init"
        exit 1
    fi
    
    echo "📥 安装 Python 依赖..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$SCRIPT_DIR/requirements.txt"
    touch "$VENV_DIR/.dependencies_installed"
    echo "✅ 依赖安装完成"
}

# 删除虚拟环境
clean_venv() {
    if [ -d "$VENV_DIR" ]; then
        echo "🗑️  删除虚拟环境..."
        rm -rf "$VENV_DIR"
        echo "✅ 虚拟环境已删除"
    else
        echo "⚠️  虚拟环境不存在"
    fi
}

# 重置虚拟环境
reset_venv() {
    clean_venv
    init_venv
}

# 进入虚拟环境 Shell
enter_shell() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "❌ 虚拟环境不存在，请先运行: ./setup.sh init"
        exit 1
    fi
    
    echo "🐚 进入虚拟环境 Shell（输入 exit 退出）"
    source "$VENV_DIR/bin/activate"
    bash
}

# 主逻辑
case "${1:-help}" in
    init)
        init_venv
        ;;
    install)
        install_deps
        ;;
    clean)
        clean_venv
        ;;
    reset)
        reset_venv
        ;;
    shell)
        enter_shell
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ 未知命令: $1"
        show_help
        exit 1
        ;;
esac
