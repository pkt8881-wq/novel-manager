@echo off
chcp 65001 > nul
echo.
echo  ====================================
echo   미로(Miro) 퀴즈 문제 대량 생성기
echo   각 장르당 100문제 목표
echo  ====================================
echo.
cd /d "%~dp0\.."
python quiz-game/generate_questions.py %*
echo.
echo 생성 완료!
pause
