@echo off
chcp 65001 > nul
title SiliconFlow语音工具
echo 正在启动 SiliconFlow 语音工具...
echo 请稍等，这可能需要几秒钟时间...

REM 检查 Python 是否已安装
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    echo 可以从 https://www.python.org/downloads/ 下载
    pause
    exit /b 1
)

REM 检查依赖是否已安装
python -c "import streamlit" > nul 2>&1
if errorlevel 1 (
    echo 正在安装所需依赖...
    pip install -r requirements.txt
)

REM 启动应用
echo 启动应用中...
python -m streamlit run tts_or_stt.py --server.port 8501
pause