@echo off
chcp 65001 >nul
echo 무협지 뷰어 시작 중...
taskkill /f /fi "windowtitle eq 무협뷰어" >nul 2>&1
start "무협뷰어" python "%~dp0server.py"
timeout /t 2 >nul
start http://localhost:8906
