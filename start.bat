@echo off
REM LangGraph 多智能体助手 - 一键启动脚本 (Windows)

echo 🚀 启动 LangGraph 多智能体助手...
echo ================================

cd /d "%~dp0"

echo.
echo 📡 后端地址: http://localhost:8000
echo 🌐 前端地址: http://localhost:3000
echo.
echo 按 Ctrl+C 停止服务
echo ================================
echo.

REM 启动后端（新窗口）
start "后端服务" cmd /k "python main.py"

REM 等待后端启动
timeout /t 3 /nobreak > nul

REM 启动前端（新窗口）
start "前端服务" cmd /k "cd frontend && npm run dev"

echo 服务已启动！请查看新开的窗口。
pause
