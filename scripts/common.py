#!/usr/bin/env python3
"""Utilidades compartidas del harness (rutas, slug, binario, claves)."""
import os, re, sys, unicodedata
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT    = SCRIPTS.parent
DATA    = ROOT / "data"
WORK    = ROOT / "work"; RAW = ROOT / "raw"; LOGS = ROOT / "logs"
DB      = ROOT / "db";   STATE = ROOT / "state"; REPORTS = ROOT / "reports"
COMUNAS = DATA / "comunas-chile.csv"
KEYWORDS= DATA / "keywords.txt"
MASTER          = DB / "chile.csv"               # base canónica (build_master, leída por panel/analysis)
MASTER_INTERNAL = DB / "_orchestrator_master.csv" # dedup interno del orquestador (no leer)
STATEF  = STATE / "state.json"
HEALTH  = STATE / "health.json"
INTEG   = STATE / "integrity.json"

IS_WIN  = os.name == "nt"
BIN     = ROOT / "google-maps-scraper" / ("google_maps_scraper.exe" if IS_WIN else "google_maps_scraper")

for d in (WORK, RAW, LOGS, DB, STATE, REPORTS):
    d.mkdir(parents=True, exist_ok=True)

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def task_slug(comuna, region):
    return slug(f"{comuna}-{region}")

def disk_free_gb():
    import shutil
    return shutil.disk_usage(str(ROOT)).free / 1e9

def find_worker_pids(s):
    """PIDs de procesos scraper cuya cmdline referencia el csv de la tarea <s>. Usa psutil."""
    try:
        import psutil
    except ImportError:
        return []
    pids = []
    needle = f"{s}.csv"
    for p in psutil.process_iter(["cmdline"]):
        try:
            cl = " ".join(p.info["cmdline"] or [])
            if "google_maps_scraper" in cl and needle in cl:
                pids.append(p.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return pids

def count_scrapers():
    try:
        import psutil
    except ImportError:
        return -1
    n = 0
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            if "google_maps_scraper" in " ".join(p.info["cmdline"] or []):
                n += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return n

def kill_pid(pid):
    try:
        import psutil
        psutil.Process(pid).kill()
    except Exception:
        try: os.kill(pid, 9)
        except Exception: pass
