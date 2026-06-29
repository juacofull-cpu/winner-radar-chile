# setup.ps1 - Instalación completa del harness en Windows.
# Uso:  powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "== Winner Radar Chile - setup (Windows) ==" -ForegroundColor Cyan

# 1) Go
if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
  Write-Host "Instalando Go con winget..."
  winget install --id GoLang.Go -e --accept-source-agreements --accept-package-agreements
  $env:Path += ";C:\Program Files\Go\bin"
}
go version

# 2) Python (debe estar instalado) + dependencias
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Instalando Python con winget..."
  winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
  $env:Path += ";$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts"
}
python --version
python -m pip install --quiet --upgrade pip
python -m pip install --quiet psutil openpyxl requests

# 3) Clonar y compilar el scraper de gosom (MIT)
if (-not (Test-Path "google-maps-scraper")) {
  Write-Host "Clonando google-maps-scraper..."
  git clone https://github.com/gosom/google-maps-scraper.git
}
Push-Location google-maps-scraper
Write-Host "Compilando google_maps_scraper.exe (puede tardar)..."
go build -o google_maps_scraper.exe .

# 4) Instalar Chromium para Playwright
Write-Host "Instalando Chromium (Playwright)..."
$env:PLAYWRIGHT_INSTALL_ONLY = "1"
.\google_maps_scraper.exe
Remove-Item Env:\PLAYWRIGHT_INSTALL_ONLY
Pop-Location

Write-Host "== LISTO ==" -ForegroundColor Green
Write-Host "Abre Claude Code en esta carpeta y segui las instrucciones de CLAUDE.md."
Write-Host "O arranca manual:  set WORKERS=6 && run.bat   y luego   stats.bat"
