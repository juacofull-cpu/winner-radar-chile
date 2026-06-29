@echo off
REM Lanza el orquestador del scrape de Chile en segundo plano (Windows).
cd /d "%~dp0"
if not exist logs mkdir logs
echo Iniciando orquestador (WORKERS=%WORKERS%)...
start "winner-radar-chile" /min cmd /c "python scripts\orchestrator.py > logs\orchestrator.log 2>&1"
echo Orquestador lanzado. Ejecuta stats.bat para ver el panel.
