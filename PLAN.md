# PLAN — Cómo scrapeamos todo Chile

## Objetivo
Construir una base de datos nacional de tiendas/negocios de Chile (nombre, dirección, comuna,
región, teléfono, estrellas, reseñas, categoría, web, email opcional), **comuna por comuna**,
agotando keywords, deduplicando por `place_id`. El Gran Santiago (34 comunas) ya está hecho y se
excluye.

## Estrategia: por prioridad geográfica
`data/comunas-chile.csv` trae 247 comunas con un campo `prioridad`. El orquestador procesa la cola
de menor a mayor prioridad, así que **las zonas con más comercio salen primero**:

| Prio | Qué incluye | Comunas |
|---|---|---|
| **1** | 3 grandes conurbaciones tras Santiago: **Gran Concepción** (11), **Gran Valparaíso** (5), **La Serena–Coquimbo** (2) | 18 |
| **2** | Capitales regionales y ciudades grandes (Antofagasta, Temuco, Iquique, Rancagua, Talca, Valdivia, Pto Montt, Arica, Chillán, Los Ángeles, Calama, Copiapó, Ovalle, Punta Arenas…) | 21 |
| **3** | Ciudades medianas y polos turístico-comerciales (Pucón, Villarrica, Castro, Quillota, San Antonio, Curicó, Linares, San Fernando…) | 71 |
| **4** | Comunas RM fuera del Gran Santiago + capitales provinciales + resto | 137 |

Total ≈ 247 comunas × ~68 keywords. El usuario deja corriendo hasta donde quiera; siempre se
cubren primero las de mayor valor.

## Keywords
`data/keywords.txt` (~68 rubros de alto valor comercial: comida, retail, salud, automotriz,
belleza, servicios, etc.). Para acercarse al 100% de cobertura, **agregar más rubros** a ese
archivo (la cobertura de "todas las tiendas" depende tanto de las comunas como de las keywords).

## Arquitectura del arnés
- **orchestrator.py** — despliega `WORKERS` procesos del scraper en paralelo (1 = 1 comuna), merge
  + dedup al cerrar. Reanudable (`state/state.json`).
- **watchdog.py** — mata workers colgados (vía `psutil`), guardia de disco (pausa si <1GB),
  registra comunas vacías para reproceso.
- **selfcheck.py** — "se consulta a sí mismo si lo que hace está bien": valida dedup, cobertura,
  comunas vacías, disco, errores; emite `state/health.json` (OK/ALERTA).
- **build_master.py** — reconstruye `db/chile.csv` desde los raw (fuente de verdad, con comuna+region).
- **panel.py** — la tabla grande de estadísticas para el loop.
- **analysis.py / dashboard.html / export_final.py** — inteligencia de ventas (tiers de oportunidad,
  tipo de teléfono celular/fijo, filtros, Excel).

## Escala y advertencias
- En el PC dedicado (Ryzen 7 / 32 GB): `WORKERS=6–8` es cómodo. La GPU (RTX 3070) no aporta al
  scraping (Chromium no la usa).
- **Sin proxies**, a escala nacional Google puede empezar a limitar. El binario soporta `-proxies`
  (variable `PROXIES`). Si aparecen bloqueos, el watchdog lo detecta; bajar `WORKERS` o poner
  proxies residenciales. Para una pasada nacional completa, los proxies son muy recomendables.
- `EMAIL=1` multiplica el tiempo (visita cada web) y genera más temporales de Chromium; úsalo en
  una segunda pasada de enriquecimiento, no en la pasada de cobertura.
- La máquina puede suspenderse: el estado es persistente, el sistema **reanuda solo** al despertar.

## Resultado y retorno
El proceso vive en este repo; **solo las bases de datos** (`db/chile.csv`, `reports/*.xlsx`) se
traen de vuelta. Esos archivos están en `.gitignore` (no se versionan): se copian/transfieren manual.
