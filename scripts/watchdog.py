#!/usr/bin/env python3
"""
Watchdog: mata workers colgados (log sin actividad > THRESHOLD), registra comunas 'done'
con raw vacío para reproceso, y aplica guardia de disco (pausa de emergencia).
Multiplataforma vía psutil (common.find_worker_pids / kill_pid). Corre en cada tick del loop.
"""
import json, os, signal, time
import common as C

THRESHOLD   = int(os.getenv("HANG_THRESHOLD", "180"))
MIN_ROWS    = int(os.getenv("MIN_ROWS", "5"))
MIN_DISK_GB = float(os.getenv("MIN_DISK_GB", "1.0"))
REPROC      = C.STATE / "needs_reprocess.txt"

def rows(p):
    if not p.exists(): return 0
    with open(p, "rb") as f:
        return max(sum(1 for _ in f) - 1, 0)

def disk_guard():
    free = C.disk_free_gb()
    if free < MIN_DISK_GB:
        try:
            pid = int((C.STATE / "orchestrator.pid").read_text().strip())
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        import psutil
        for p in psutil.process_iter(["cmdline"]):
            try:
                if "google_maps_scraper" in " ".join(p.info["cmdline"] or []): p.kill()
            except Exception: pass
        print(f"[watchdog] DISCO CRITICO {free:.2f}GB < {MIN_DISK_GB} -> PAUSA DE EMERGENCIA")
        return True
    return False

def main():
    if not C.STATEF.exists(): return
    if disk_guard(): return
    st = json.loads(C.STATEF.read_text(encoding="utf-8"))
    now = time.time(); killed = []; reproc = []
    for s, d in st["tasks"].items():
        log = C.LOGS / f"{s}.log"
        if d["status"] == "running" and log.exists():
            if now - log.stat().st_mtime > THRESHOLD:
                pids = C.find_worker_pids(s)
                for pid in pids: C.kill_pid(pid)
                if pids: killed.append(f"{d['comuna']} ({d['region']})")
        if d["status"] == "done" and rows(C.RAW / f"{s}.csv") < MIN_ROWS:
            reproc.append(f"{d['comuna']}|{d['region']}")
    if reproc:
        ex = set(REPROC.read_text(encoding="utf-8").split("\n")) if REPROC.exists() else set()
        ex.update(reproc); ex.discard("")
        REPROC.write_text("\n".join(sorted(ex)) + "\n", encoding="utf-8")
    if killed or reproc:
        print(f"[watchdog] colgados matados: {killed or '—'} | a reprocesar: {len(reproc)}")

if __name__ == "__main__":
    main()
