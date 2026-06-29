#!/bin/bash
# setup.sh - Instalación del harness en Linux/Mac (equivalente a setup.ps1).
set -e
cd "$(dirname "$0")"
echo "== Winner Radar Chile - setup (Linux/Mac) =="

# 1) Go
if ! command -v go >/dev/null 2>&1; then
  echo "Falta Go. Instálalo:  brew install go   (Mac)  |  sudo apt install golang-go  (Debian/Ubuntu)"
  echo "o descarga el tarball de https://go.dev/dl/ y agrégalo al PATH. Luego re-corre setup.sh."
  exit 1
fi
go version

# 2) Python deps
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet psutil openpyxl requests

# 3) Clonar y compilar gosom (MIT)
[ -d google-maps-scraper ] || git clone https://github.com/gosom/google-maps-scraper.git
( cd google-maps-scraper && echo "Compilando..." && go build -o google_maps_scraper . \
  && echo "Instalando Chromium..." && PLAYWRIGHT_INSTALL_ONLY=1 ./google_maps_scraper )

echo "== LISTO =="
echo "Arranca:  WORKERS=6 ./run.sh   y luego   ./stats.sh   (o sigue CLAUDE.md con Claude Code)"
