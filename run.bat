@echo off
chcp 65001 >nul
echo ========================================
echo   Tricard 斗地主 - 一键启动
echo ========================================
echo.

:: 检查环境
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到 .venv，请先运行 uv venv 创建环境
    pause
    exit /b 1
)

:: 安装后端依赖
echo [1/4] 检查后端依赖...
.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt 2>nul

:: 确保数据库和 AI 账号
echo [2/4] 初始化数据库与 AI 账号...
.venv\Scripts\python.exe backend\scripts\seed_ai.py --ensure >nul

:: 构建前端
echo [3/4] 构建前端...
cd frontend
call npm install --silent 2>nul
call npx vite build --logLevel error
cd ..

:: 启动服务
echo [4/4] 启动服务（端口 8000）...
echo.
echo   局域网其他设备访问: http://<本机IP>:8000
echo   按 Ctrl+C 停止服务
echo.
.venv\Scripts\python.exe -m uvicorn app.main:sio_app --app-dir backend --host 0.0.0.0 --port 8000

pause