#!/usr/bin/env python3
"""Panel de estadísticas del scrape de Chile. Lee state.json + raw/ + chile.csv + health.json."""
import csv, json, sys, time
import common as C

csv.field_size_limit(sys.maxsize)

def bar(v, t, w=24):
    t = max(t, 1); f = min(int(v * w / t), w); return "█" * f + "░" * (w - f)
def hhmm(s):
    s = int(max(s, 0)); return f"{s//3600}h{(s%3600)//60:02d}m" if s >= 3600 else f"{s//60}m{s%60:02d}s"
def crows(p):
    if not p.exists(): return 0
    with open(p, "rb") as f: return max(sum(1 for _ in f) - 1, 0)

def master_stats():
    tel = mail = web = tot = 0; by_reg = {}
    if not C.MASTER.exists(): return tot, tel, mail, web, by_reg
    with open(C.MASTER, newline="", encoding="utf-8") as f:
        for x in csv.DictReader(f):
            tot += 1
            if x.get("phone", "").strip(): tel += 1
            if x.get("emails", "").strip(): mail += 1
            if x.get("website", "").strip(): web += 1
            r = x.get("region", "?"); by_reg[r] = by_reg.get(r, 0) + 1
    return tot, tel, mail, web, by_reg

def main():
    if not C.STATEF.exists():
        print("⏳ Orquestador no iniciado."); return
    st = json.loads(C.STATEF.read_text(encoding="utf-8")); cfg = st.get("config", {})
    T = st["tasks"]; now = int(time.time())
    done = [s for s in T if T[s]["status"] == "done"]
    run  = [s for s in T if T[s]["status"] == "running"]
    pend = [s for s in T if T[s]["status"] == "pending"]
    tot, tel, mail, web, by_reg = master_stats()
    integ = json.loads(C.INTEG.read_text(encoding="utf-8")) if C.INTEG.exists() else {}
    health = json.loads(C.HEALTH.read_text(encoding="utf-8")) if C.HEALTH.exists() else {}
    raw_live = sum(crows(C.RAW / f"{s}.csv") for s in run)
    pct = lambda a, b: f"{(100*a//b) if b else 0}%"
    W = 80
    p = lambda s: print("║ " + s.ljust(W - 1) + "║")
    print("╔" + "═" * W + "╗")
    print("║" + " 🇨🇱  BASE DE DATOS CHILE · scrape multi-agente ".center(W) + "║")
    print("╠" + "═" * W + "╣")
    p(f"⏱ {hhmm(now-st.get('started_at',now))}  Workers {cfg.get('workers','?')}  Depth {cfg.get('depth','?')}  "
      f"Email {'sí' if cfg.get('email') else 'no'}  Proxy {'sí' if cfg.get('proxies') else 'no'}")
    p(f"Comunas: {len(done)}/{len(T)}  [{bar(len(done),len(T))}]  {pct(len(done),len(T))}")
    print("╟" + "─" * W + "╢")
    p(f"📊 EN BASE: {tot} únicos · tel {pct(tel,tot)} · email {pct(mail,tot)} · web {pct(web,tot)}")
    p(f"📥 Capturando ahora (crudo): +{raw_live} en {len(run)} comunas activas")
    p(f"🧹 {integ.get('dup_cross',0)} dup cross-comuna descartados (dedup global place_id)")
    hv = health.get("verdict", "—")
    p(f"🩺 Self-check: {hv}" + ("" if hv == "OK" else "  ⚠️ " + " | ".join(health.get("alerts", [])[:2])))
    print("╟" + "─" * W + "╢")
    p("🟢 WORKERS ACTIVOS")
    p(f"  {'COMUNA':<22}{'REGIÓN':<18}{'NEG':>6}{'TIEMPO':>9}")
    for s in run[:8]:
        d = T[s]; el = hhmm(now - (d.get("started_at") or now))
        p(f"  {d['comuna'][:21]:<22}{d['region'][:17]:<18}{crows(C.RAW/f'{s}.csv'):>6}{el:>9}")
    if not run: p("  (ninguno)")
    print("╟" + "─" * W + "╢")
    p("🗺  EN BASE POR REGIÓN")
    if by_reg:
        items = sorted(by_reg.items(), key=lambda i: -i[1]); mx = items[0][1]
        for r, k in items[:8]:
            p(f"  {r[:20]:<20}{k:>6}  {bar(k, mx, 20)}")
    else: p("  (poblando…)")
    print("╟" + "─" * W + "╢")
    nxt = ", ".join(T[s]["comuna"] for s in pend[:6])
    p(f"⏳ EN COLA ({len(pend)}): {nxt}{'…' if len(pend)>6 else ''}")
    p(f"💾 Disco libre: {round(C.disk_free_gb(),1)} GB")
    print("╚" + "═" * W + "╝")

if __name__ == "__main__":
    main()
