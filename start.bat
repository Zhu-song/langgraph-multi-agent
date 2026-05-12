@echo off
chcp 65001 >nul 2>&1
REM LangGraph 多智能体助手 - 一键启动脚本 (Windows)

echo.
echo 🚀 启动 LangGraph 多智能体助手...
echo ================================

REM 切换到脚本所在目录
cd /d "%~dp0"

set "SCRIPT_DIR=%cd%"
set "VENV_DIR=%SCRIPT_DIR%\venv"

REM ======================
REM 检查 Python 是否安装
REM ======================
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 python，请先安装 Python 3.10+
    echo    下载地址: https://www.python.org/downloads/
    echo    安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VER=%%v
echo 📋 Python 版本: %PYTHON_VER%

REM ======================
REM 检查并创建虚拟环境
REM ======================
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo 📦 创建 Python 虚拟环境...
    if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo ❌ 创建虚拟环境失败，请确保已安装 python3-venv
        pause
        exit /b 1
    )

    REM 配置 pip 清华镜像源（加速下载）
    echo ⚙️  配置 pip 清华镜像源...
    if not exist "%VENV_DIR%" mkdir "%VENV_DIR%"
    (
        echo [global]
        echo index-url = https://pypi.tuna.tsinghua.edu.cn/simple
        echo trusted-host = pypi.tuna.tsinghua.edu.cn
    ) > "%VENV_DIR%\pip.ini"

    echo ✅ 虚拟环境创建完成
) else (
    echo ✅ 虚拟环境检查完成
)

REM ======================
REM 激活虚拟环境
REM ======================
call "%VENV_DIR%\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo ❌ 激活虚拟环境失败
    pause
    exit /b 1
)

echo ✅ 虚拟环境已激活

REM ======================
REM 检查并安装依赖
REM ======================
set NEED_INSTALL=false

if not exist "%VENV_DIR%\.dependencies_installed" set NEED_INSTALL=true
if exist "%SCRIPT_DIR%\requirements.txt" (
    if exist "%VENV_DIR%\.dependencies_installed" (
        copy /b "%SCRIPT_DIR%\requirements.txt"+,, "%VENV_DIR%\.dependencies_installed.tmp" >nul 2>&1
        fc /b "%SCRIPT_DIR%\requirements.txt" "%VENV_DIR%\.dependencies_installed" >nul 2>&1
        if %errorlevel% neq 0 set NEED_INSTALL=true
        del "%VENV_DIR%\.dependencies_installed.tmp" >nul 2>&1
    )
)

python -c "import langchain" >nul 2>&1
if %errorlevel% neq 0 set NEED_INSTALL=true

if "%NEED_INSTALL%"=="true" (
    echo 📥 安装 Python 依赖...
    pip install --upgrade pip -q
    if %errorlevel% neq 0 (
        echo ❌ pip 升级失败
        pause
        exit /b 1
    )

    pip install -r "%SCRIPT_DIR%\requirements.txt" -q
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )

    pip install "httpx[socks]" -q 2>nul

    REM 记录安装时间戳
    copy /b "%SCRIPT_DIR%\requirements.txt" "%VENV_DIR%\.dependencies_installed" >nul 2>&1
    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖检查完成
)

REM ======================
REM 检查 .env 文件
REM ======================
if not exist "%SCRIPT_DIR%\.env" (
    echo ⚠️  未找到 .env 文件，请确保已配置环境变量
    echo    可以复制 .env.example 并修改：
    echo    copy .env.example .env
)

REM ======================
REM 检查是否安装了 concurrently
REM ======================
where concurrently >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 安装 concurrently...
    call npm install -g concurrently 2>nul
)

REM ======================
REM 检查端口占用
REM ======================
netstat -ano | findstr ":8000" >nul 2>&1
if %errorlevel% equ 0 (
    echo ⚠️  端口 8000 已被占用，可能会影响后端服务启动
)

netstat -ano | findstr ":3000" >nul 2>&1
if %errorlevel% equ 0 (
    echo ⚠️  端口 3000 已被占用，可能会影响前端服务启动
)

REM ======================
REM 启动服务
REM ======================
echo.
echo 📡 后端地址: http://localhost:8000
echo 🌐 前端地址: http://localhost:3000
echo.
echo 按 Ctrl+C 停止服务
echo ================================
echo.

REM 使用 concurrently 在同一窗口启动前后端
concurrently -n "后端,前端" -c "blue,green" "%VENV_DIR%\Scripts\python.exe main.py" "cd frontend && npm run dev"

REM 如果 concurrently 不可用，回退到双窗口模式
if %errorlevel% neq 0 (
    echo ⚠️  concurrently 启动失败，使用独立窗口模式...
    echo.
    start "后端服务" cmd /k "%VENV_DIR%\Scripts\python.exe main.py"
    timeout /t 3 /nobreak > nul
    start "前端服务" cmd /k "cd frontend && npm run dev"
    echo 服务已启动！请查看新开的窗口。
    pause
)
