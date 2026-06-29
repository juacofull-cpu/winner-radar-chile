# 🇨🇱 Winner Radar Chile — Harness de scraping de tiendas

Sistema multi-agente para **scrapear todas las tiendas de Chile** (comuna por comuna, por orden de
prioridad) usando el scraper open-source [`gosom/google-maps-scraper`](https://github.com/gosom/google-maps-scraper)
como motor y un "arnés" de orquestación, watchdog, auto-verificación y panel de estadísticas en loop.

Pensado para correr en un **PC dedicado encendido 24/7** (Windows nativo, pero corre igual en
Linux/Mac). El Gran Santiago ya fue scrapeado aparte, así que **este harness cubre el resto de Chile**.

## Instalación (Windows)
```powershell
git clone <este-repo>
cd winner-radar-chile
powershell -ExecutionPolicy Bypass -File setup.ps1
```
`setup.ps1` instala Go, las dependencias de Python (`psutil`, `openpyxl`), clona y compila el
scraper de gosom (`google-maps-scraper.exe`) y baja Chromium.

> Linux/Mac: usa `./setup.sh` (requiere Go instalado).

## Uso
**Opción A — con Claude Code (recomendado, autónomo):** abre Claude Code en esta carpeta. El
archivo [`CLAUDE.md`](CLAUDE.md) le indica cómo arrancar el orquestador, correr el loop cada 5 min
y auto-verificarse. Usa `/loop` para que reporte estadísticas solo.

**Opción B — manual:**
```bat
set WORKERS=6
run.bat            REM lanza el orquestador en segundo plano
stats.bat          REM panel + watchdog + self-check (córrelo cuando quieras)
```

## Configuración (variables de entorno)
| Variable | Default | Qué hace |
|---|---|---|
| `WORKERS` | 6 | comunas en paralelo (sube a 8 con 32GB RAM) |
| `EMAIL` | 0 | `1` = entra a cada web a sacar correos (más lento) |
| `DEPTH` | 8 | profundidad de scroll por keyword |
| `CONC` | 2 | páginas concurrentes por worker |
| `PROXIES` | — | lista `protocolo://user:pass@host:port,...` (recomendado a escala nacional) |
| `LIMIT_COMUNAS`/`LIMIT_KEYWORDS` | 0 | límites para pruebas |

## Estructura
```
data/      comunas-chile.csv (247 comunas, prioridad) · keywords.txt (~68 rubros)
scripts/   orchestrator · watchdog · build_master · selfcheck · panel · analysis · export_final · common
run.bat/.sh · stats.bat/.sh · setup.ps1/.sh
analysis/  dashboard.html + chart.min.js (informe dinámico; data.json se genera)
# raw/ db/ state/ logs/ reports/  -> se crean al correr (no se versionan)
```

## Salidas
- `db/chile.csv` — base canónica deduplicada (con comuna y región).
- `reports/chile-tiendas.xlsx` — Excel filtrable.
- `analysis/dashboard.html` — informe dinámico (tiers de oportunidad, filtros, gráficos).

Ver [`PLAN.md`](PLAN.md) para la estrategia de cobertura y priorización.
Motor de scraping: `gosom/google-maps-scraper` (licencia MIT).
