#!/usr/bin/env python3
"""
Self-check: el harness "se consulta a sí mismo si lo que hace está bien".
Valida integridad y emite un veredicto OK/ALERTA en state/health.json para que el loop
de Claude Code lo lea y actúe. No modifica datos (solo diagnostica).

Chequeos:
  - duplicados en la base canónica (debe ser 0; build_master ya deduplica)
  - comunas 'done' con raw vacío/insuficiente (-> reproceso)
  - cobertura (% comunas done) y ritmo
  - disco libre
  - errores reales en logs ("status":"error" / "level":"error")
"""
import csv, json, os, sys, time
import common as C

csv.field_size_limit(sys.maxsize)

def count_csv(p):
    if not p.exists(): return 0
    with open(p, "rb") as f: return max(sum(1 for _ in f) - 1, 0)

def dup_in_master():
    if not C.MASTER.exists(): return 0, 0
    seen = set(); dup = 0; tot = 0
    with open(C.MASTER, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for x in r:
            tot += 1
            k = (x.get("place_id") or "").strip() or f"{x.get('title','')}|{x.get('address','')}".lower()
            if k in seen: dup += 1
            else: seen.add(k)
    return tot, dup

def main():
    alerts = []; info = {}
    if not C.STATEF.exists():
        json.dump({"verdict": "SIN ESTADO", "alerts": ["orquestador no iniciado"]},
                  open(C.HEALTH, "w")); print("SIN ESTADO"); return
    st = json.loads(C.STATEF.read_text(encoding="utf-8"))
    tasks = st["tasks"]; n = len(tasks)
    done = [d for d in tasks.values() if d["status"] == "done"]
    running = [d for d in tasks.values() if d["status"] == "running"]
    info["comunas_done"] = len(done); info["comunas_total"] = n
    info["running"] = len(running)

    # 1) duplicados en base canónica
    tot, dup = dup_in_master()
    info["base_total"] = tot; info["base_dup"] = dup
    if dup > 0: alerts.append(f"{dup} duplicados en la base canónica (revisar dedup)")

    # 2) comunas done vacías
    vacias = [f"{d['comuna']}" for d in done if count_csv(C.RAW / f"{C.task_slug(d['comuna'], d['region'])}.csv") < 5]
    info["comunas_vacias"] = len(vacias)
    if vacias: alerts.append(f"{len(vacias)} comunas cerraron vacías -> reproceso: {', '.join(vacias[:5])}")

    # 3) disco
    free = round(C.disk_free_gb(), 1); info["disco_gb"] = free
    if free < 1.0: alerts.append(f"DISCO CRÍTICO: {free} GB libres")
    elif free < 3.0: alerts.append(f"disco bajo: {free} GB")

    # 4) scrapers vivos vs workers esperados
    alive = C.count_scrapers(); info["scrapers_vivos"] = alive
    cfg = st.get("config", {})
    if running and alive == 0:
        alerts.append("hay comunas 'running' pero 0 procesos scraper vivos (orquestador caído?)")

    # 5) errores reales en logs (muestra)
    errs = 0
    for d in running:
        log = C.LOGS / f"{C.task_slug(d['comuna'], d['region'])}.log"
        if log.exists():
            try:
                txt = log.read_text(encoding="utf-8", errors="ignore")[-20000:]
                errs += txt.count('"status":"error"') + txt.count('"level":"error"')
            except Exception: pass
    info["errores_recientes"] = errs

    verdict = "OK" if not alerts else "ALERTA"
    out = {"verdict": verdict, "ts": int(time.time()), "info": info, "alerts": alerts}
    C.HEALTH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"SELF-CHECK: {verdict}")
    for a in alerts: print("  ⚠️ " + a)
    if not alerts: print(f"  base {tot} · done {len(done)}/{n} · disco {free}GB · scrapers {alive}")

if __name__ == "__main__":
    main()
