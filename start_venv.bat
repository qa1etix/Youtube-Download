@echo off
chcp 65001 > nul
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

".venv\Scripts\python.exe" main.py

echo.
echo Программа завершила работу.
pause