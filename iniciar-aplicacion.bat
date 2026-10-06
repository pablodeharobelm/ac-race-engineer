@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Falta el entorno Python del proyecto. Consulta docs\primer-arranque.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -X utf8 -m ac_race_engineer.local_launcher %*
pause
