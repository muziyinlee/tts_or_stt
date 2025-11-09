@echo off
chcp 936 > nul
title SiliconFlow语音工具

:menu
cls
echo.
echo ================================
echo     SiliconFlow 语音工具
echo ================================
echo.
echo 请选择要执行的操作：
echo.
echo 1. 全部启动
echo 2. 启动语音工具-端口8501
echo 3. 启动密钥管理系统-端口8502
echo 4. 启动API服务器-端口8503
echo 5. 退出
echo.
set /p choice=请输入选择（1-5）:

if "%choice%"=="1" goto all
if "%choice%"=="2" goto tts
if "%choice%"=="3" goto kms
if "%choice%"=="4" goto api
if "%choice%"=="5" goto exit

echo 无效的选择，请重新输入！
timeout /t 2 > nul
goto menu

:all
echo 正在启动所有服务...
call :check_python
call :check_dependencies
echo 启动语音工具-端口8501...
start "" streamlit run tts_or_stt.py --server.port 8501
echo 启动密钥管理系统-端口8502...
start "" streamlit run kms_web_interface.py --server.port 8502
echo 启动API服务器-端口8503...
start "" python kms_api_server.py
echo 所有服务已启动！
pause
goto menu

:tts
echo 启动语音工具-端口8501...
call :check_python
call :check_dependencies
start "" streamlit run tts_or_stt.py --server.port 8501
echo 语音工具已启动！
pause
goto menu

:kms
echo 启动密钥管理系统-端口8502...
call :check_python
call :check_dependencies
start "" streamlit run kms_web_interface.py --server.port 8502
echo 密钥管理系统已启动！
pause
goto menu

:api
echo 启动API服务器-端口8503...
call :check_python
python -c "import flask, requests" > nul 2>&1
if errorlevel 1 (
    echo 正在安装API服务器所需依赖...
    pip install flask requests
)
start "" python kms_api_server.py
echo API服务器已启动！
pause
goto menu

:exit
echo 退出SiliconFlow语音工具...
exit /b 0

:check_python
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    echo 可以从 https://www.python.org/downloads/ 下载
    pause
    exit /b 1
)
goto :eof

:check_dependencies
python -c "import streamlit" > nul 2>&1
if errorlevel 1 (
    echo 正在安装所需依赖...
    pip install -r requirements.txt
)
goto :eof