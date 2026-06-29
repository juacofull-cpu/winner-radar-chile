#!/bin/bash
# Tick del arnés: watchdog + base + self-check + panel (Linux/Mac). Equivalente a stats.bat.
cd "$(dirname "$0")" || exit 1
python3 scripts/watchdog.py
python3 scripts/build_master.py >/dev/null 2>&1
python3 scripts/selfcheck.py
python3 scripts/panel.py
