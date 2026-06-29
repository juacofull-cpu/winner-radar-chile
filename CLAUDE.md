# CLAUDE.md — Arnés de scraping de Chile

Eres el operador autónomo de este sistema. Tu trabajo es **scrapear todas las tiendas de Chile
(menos el Gran Santiago, ya hecho), comuna por comuna, por orden de prioridad**, manteniendo el
sistema sano y reportando estadísticas en un loop. El usuario te deja trabajando solo; su única
visualización son las estadísticas que le entregas. Comunícate en español, directo y sin relleno.

## Qué es este repo
Harness multi-agente sobre el scraper `gosom/google-maps-scraper`. El "agente que orquesta agentes"
es `scripts/orchestrator.py`: lanza N *workers* (procesos del scraper) en paralelo, 1 worker = 1
comuna, agotando todas las keywords. Al cerrar una comuna, mergea a la base deduplicando por
`place_id`. Todo es **reanudable** (estado en `state/state.json`).

## Arranque (una vez)
1. `powershell -ExecutionPolicy Bypass -File setup.ps1`  (instala Go, deps, clona+compila gosom, baja Chromium)
2. Verifica: existe `google-maps-scraper/google_maps_scraper.exe`.

## Operación en LOOP (lo que haces siempre)
1. Si el orquestador no está corriendo, arráncalo:  `run.bat`  (Windows) / `./run.sh` (Linux/Mac).
   Variables útiles antes de arrancar: `WORKERS` (def 6; sube a 8 si la RAM aguanta), `EMAIL=1`
   (más lento, saca correos), `PROXIES` (lista separada por comas si tienes proxies).
2. Cada ~5 minutos ejecuta el tick:  `stats.bat`  (Windows) / `./stats.sh`.
   Eso corre, en orden: **watchdog → build_master → selfcheck → panel**. Reporta al usuario el
   panel (la tabla grande) tal cual.
3. **Actúa ante lo que diga el self-check** (`state/health.json`, también impreso por `stats.bat`):
   - `comunas cerraron vacías` → están en `state/needs_reprocess.txt`; reprócesalas lanzando el
     scraper solo para ellas (ver Recetas) o reiníciando el orquestador (las toma como pending).
   - `0 procesos scraper vivos` pero hay comunas `running` → el orquestador se cayó: relánzalo.
   - `disco bajo/crítico` → el watchdog ya pausa si <1GB; libera espacio antes de seguir.
   - `duplicados en la base` → no debería pasar (build_master deduplica); investiga el merge.
   - señales de bloqueo de Google (muchos errores) → baja `WORKERS` o configura `PROXIES`.
4. Mantén el loop con `/loop` de Claude Code (cada 5 min). Es la "memoria que se consulta a sí
   misma": el selfcheck valida integridad en cada tick y tú reaccionas.

## El objetivo y el orden
- Cola = `data/comunas-chile.csv` (247 comunas con `prioridad`). Se procesan prioridad 1 → 4
  (áreas metropolitanas primero: Gran Concepción, Gran Valparaíso, La Serena-Coquimbo, etc.).
- Keywords = `data/keywords.txt` (~68 rubros). Para ampliar cobertura, agrega más rubros aquí.

## Entregables (cuando el usuario los pida o al avanzar harto)
- `python scripts/build_master.py` → `db/chile.csv` (base canónica con comuna+region).
- `python scripts/analysis.py` → `analysis/data.json` (tiers + tipo de teléfono).
- abre `analysis/dashboard.html` (informe dinámico filtrable).
- `python scripts/export_final.py` → `reports/chile-tiendas.xlsx`.
- **Solo las bases de datos (`db/`, `reports/`) se traen de vuelta** al usuario; el resto es proceso.

## FASE 2 — Enriquecer emails (cuando la cobertura ya avanzó)
La pasada de cobertura va SIN email (rápida). Para sacar correos, corre la fase 2 sobre la base:
`python scripts/enrich_emails.py`  (visita las webs de los negocios con HTTP plano, concurrente,
SIN navegador → rápido, liviano, no toca Google). Aprovecha el PC: `set EMAIL_WORKERS=150` y vuela.
Es reanudable (`db/email_cache.json`) e idempotente; reescribe la columna `emails` en `db/chile.csv`.
Hazla cuando el orquestador ya haya cubierto bastante (no compite con el scraping). Esperá ~13-20%
de hits (muchos negocios no publican email).

## Recetas
- Reprocesar una comuna suelta (ej. quedó vacía):
  `./google-maps-scraper/google_maps_scraper(.exe) -input work/<slug>.txt -results raw/<slug>.csv -depth 8 -c 2 -lang es -exit-on-inactivity 90s`
  luego `python scripts/build_master.py`.
- Bajar intensidad si hay bloqueo: detén el orquestador, `set WORKERS=3`, vuelve a `run.bat`.

## Reglas
- Nunca subas datos ni `.env` a git (ya están en `.gitignore`). Este PC scrapea; los datos se exportan.
- Sé honesto en los reportes: si una comuna falló, dilo; si hay bloqueo, dilo.
- Convierte fechas relativas a absolutas en notas. Respeta que la máquina puede suspenderse: el
  sistema reanuda solo al despertar (estado persistente).
