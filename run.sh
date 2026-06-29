#!/bin/bash
# Lanza el orquestador en segundo plano (Linux/Mac). Equivalente a run.bat.
cd "$(dirname "$0")" || exit 1
mkdir -p logs
echo "Iniciando orquestador (WORKERS=${WORKERS:-6})..."
nohup python3 scripts/orchestrator.py > logs/orchestrator.log 2>&1 &
echo "Orquestador PID $!. Ejecuta ./stats.sh para ver el panel."
