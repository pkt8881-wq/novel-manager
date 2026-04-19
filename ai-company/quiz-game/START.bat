@echo off
chcp 65001 > nul
echo.
echo  =================================
echo   AI Quiz Game - port 8879
echo  =================================
echo.

:: 기존 프로세스 정리
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8879 "') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: 서버 시작
cd /d "%~dp0"
start "" "http://localhost:8879"
python server.py
pause
