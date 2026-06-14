@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动 Muse Mirror...
streamlit run app.py
pause
