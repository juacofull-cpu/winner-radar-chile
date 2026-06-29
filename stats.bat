@echo off
REM Tick del arnés: watchdog + reconstrucción de la base + self-check + panel (Windows).
cd /d "%~dp0"
python scripts\watchdog.py
python scripts\build_master.py >nul 2>&1
python scripts\selfcheck.py
python scripts\panel.py
