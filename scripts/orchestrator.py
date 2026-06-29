#!/usr/bin/env python3
"""
Orquestador del scrape de Chile (todas las comunas salvo Santiago, por prioridad).
1 worker = 1 comuna (agota todas las keywords). Mantiene WORKERS en paralelo.
Al cerrar una comuna: mergea a la base maestra deduplicando por place_id. Reanudable.
Multiplataforma (Windows/Linux/Mac). Config por variables de entorno.
"""
import csv, json, signal, subprocess, sys, time
import common as C

WORKERS  = int(__import__("os").getenv("WORKERS", "6"))
DEPTH    = int(__import__("os").getenv("DEPTH", "8"))
CONC     = int(__import__("os").getenv("CONC", "2"))
EMAIL    = __import__("os").getenv("EMAIL", "0") == "1"     # por defecto SIN email (rápido)
INACT    = __import__("os").getenv("INACT", "90s")
LANG     = __import__("os").getenv("LANG_CODE", "es")
PROXIES  = __import__("os").getenv("PROXIES", "").strip()    # opcional: lista separada por comas
LIMIT_C  = int(__import__("os").getenv("LIMIT_COMUNAS", "0"))
LIMIT_K  = int(__import__("os").getenv("LIMIT_KEYWORDS", "0"))

def now(): return int(time.time())

def load_tasks():
    tasks = []
    with open(C.COMUNAS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tasks.append((r["comuna"], r["region"], int(r["prioridad"])))
    tasks.sort(key=lambda t: (t[2], t[1], t[0]))   # por prioridad asc
    if LIMIT_C > 0: tasks = tasks[:LIMIT_C]
    return tasks

def load_keywords():
    kw = [l.strip() for l in C.KEYWORDS.read_text(encoding="utf-8").splitlines() if l.strip()]
    return kw[:LIMIT_K] if LIMIT_K > 0 else kw

def load_state(tasks):
    st = json.loads(C.STATEF.read_text(encoding="utf-8")) if C.STATEF.exists() else {
        "started_at": now(), "tasks": {}, "config": {}}
    for comuna, region, prio in tasks:
        s = C.task_slug(comuna, region)
        st["tasks"].setdefault(s, {"comuna": comuna, "region": region, "prioridad": prio,
            "status": "pending", "raw": 0, "added": 0, "dup": 0,
            "started_at": None, "finished_at": None})
    for d in st["tasks"].values():            # corrida previa interrumpida
        if d["status"] == "running": d["status"] = "pending"
    st["config"] = {"workers": WORKERS, "depth": DEPTH, "conc": CONC, "email": EMAIL,
                    "inact": INACT, "proxies": bool(PROXIES)}
    return st

def save_state(st):
    tmp = C.STATEF.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(C.STATEF)

# ---------- dedup / merge ----------
def row_key(row, idx):
    pid = (row[idx.get("place_id", -1)] if idx.get("place_id", -1) >= 0 and idx["place_id"] < len(row) else "")
    pid = (pid or "").strip()
    if pid: return pid
    t = row[idx["title"]].strip().lower() if "title" in idx and idx["title"] < len(row) else ""
    a = row[idx["address"]].strip().lower() if "address" in idx and idx["address"] < len(row) else ""
    return f"{t}|{a}"

def load_seen():
    seen = set(); header = None
    if not C.MASTER_INTERNAL.exists(): return seen, header
    csv.field_size_limit(sys.maxsize)
    with open(C.MASTER_INTERNAL, newline="", encoding="utf-8") as f:
        r = csv.reader(f); header = next(r, None)
        if not header: return seen, None
        idx = {h: i for i, h in enumerate(header)}
        for row in r:
            if row: seen.add(row_key(row, idx))
    return seen, header

def merge(raw_csv, comuna, region, seen, master_header):
    if not raw_csv.exists(): return 0, 0, 0, master_header
    csv.field_size_limit(sys.maxsize)
    with open(raw_csv, newline="", encoding="utf-8") as f:
        r = list(csv.reader(f))
    if not r: return 0, 0, 0, master_header
    header, rows = r[0], r[1:]
    idx = {h: i for i, h in enumerate(header)}
    if master_header is None:
        master_header = ["comuna", "region"] + header
        with open(C.MASTER_INTERNAL, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(master_header)
    added = dup = 0
    with open(C.MASTER_INTERNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for row in rows:
            if not row: continue
            k = row_key(row, idx)
            if k in seen: dup += 1; continue
            seen.add(k); w.writerow([comuna, region] + row); added += 1
    return len(rows), added, dup, master_header

# ---------- worker ----------
def launch(comuna, region, keywords):
    s = C.task_slug(comuna, region)
    qf = C.WORK / f"{s}.txt"
    qf.write_text("\n".join(f"{kw} in {comuna}, {region}, Chile" for kw in keywords) + "\n", encoding="utf-8")
    out = C.RAW / f"{s}.csv"
    log = open(C.LOGS / f"{s}.log", "w")
    cmd = [str(C.BIN), "-input", str(qf), "-results", str(out), "-depth", str(DEPTH),
           "-c", str(CONC), "-lang", LANG, "-exit-on-inactivity", INACT]
    if EMAIL: cmd.append("-email")
    if PROXIES: cmd += ["-proxies", PROXIES]
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    return p, log, out

def main():
    import os
    (C.STATE / "orchestrator.pid").write_text(str(os.getpid()), encoding="utf-8")
    tasks = load_tasks(); keywords = load_keywords()
    st = load_state(tasks); save_state(st)
    seen, master_header = load_seen()
    running = {}; stop = {"v": False}
    for sig in (signal.SIGTERM, signal.SIGINT):
        try: signal.signal(sig, lambda *_: stop.update(v=True))
        except Exception: pass

    order = [C.task_slug(c, r) for c, r, _ in tasks]
    def pending(): return [s for s in order if st["tasks"][s]["status"] == "pending"]

    while not stop["v"] and (pending() or running):
        while not stop["v"] and len(running) < WORKERS and pending():
            s = pending()[0]; d = st["tasks"][s]
            proc, log, out = launch(d["comuna"], d["region"], keywords)
            running[s] = (proc, log, out)
            d.update(status="running", started_at=now(), finished_at=None); save_state(st)
        done = [s for s, (p, *_2) in running.items() if p.poll() is not None]
        for s in done:
            proc, log, out = running.pop(s); log.close()
            d = st["tasks"][s]
            raw_n, added, dup, master_header = merge(out, d["comuna"], d["region"], seen, master_header)
            d.update(status="done", finished_at=now(), raw=raw_n, added=added, dup=dup)
            st["total_unique"] = len(seen); save_state(st)
        time.sleep(2)

    for s, (proc, log, out) in running.items():
        try: proc.terminate()
        except Exception: pass
        log.close(); st["tasks"][s]["status"] = "pending"
    st["total_unique"] = len(seen); save_state(st)

if __name__ == "__main__":
    main()
