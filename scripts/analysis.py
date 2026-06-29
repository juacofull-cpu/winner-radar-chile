#!/usr/bin/env python3
"""
Motor de análisis de leads para Chile: score de oportunidad + tier + tipo de teléfono.
Exporta analysis/data.json para el dashboard dinámico. Misma lógica que el de Santiago,
con región añadida. A = lead más caliente (menos estrellas + menos reseñas = más desesperado).
"""
import csv, json, re, sys, statistics
from collections import Counter, defaultdict
import common as C

csv.field_size_limit(sys.maxsize)
OUTDIR = C.ROOT / "analysis"; OUTDIR.mkdir(exist_ok=True)
OUT = OUTDIR / "data.json"

def ff(x):
    try: return float(x)
    except: return 0.0
def ii(x):
    try: return int(float(x))
    except: return 0

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
BAD_EXT = (".gif", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".css", ".js", ".ico")
BAD_DOM = ("getjusto.com", "sentry.io", "wixpress.com", "godaddy.com")
def first_email(raw):
    for e in (raw or "").split(","):
        e = e.strip().lstrip(">").strip().lower(); e = re.sub(r"^u00[0-9a-f]{2}", "", e)
        if not EMAIL_RE.match(e) or e.endswith(BAD_EXT): continue
        if any(e.split("@",1)[1].endswith(d) for d in BAD_DOM): continue
        return e
    return ""
def fmt_phone(p):
    d = re.sub(r"\D", "", p or "")
    if not d: return ""
    if d.startswith("56"): d = d[2:]
    if len(d) == 9: return f"+56 {d[0]} {d[1:5]} {d[5:]}"
    if len(d) == 8: return f"+56 {d[:4]} {d[4:]}"
    return "+56 " + d
def clean_addr(t, a):
    pref = f"{t} - "; return a[len(pref):] if a.startswith(pref) else a

def rep_pts(r): return 33 if r==0 else 50 if r<3 else 42 if r<4 else 26 if r<4.5 else 12 if r<4.8 else 0
def trac_pts(v): return 50 if v==0 else 42 if v<=10 else 32 if v<=30 else 20 if v<=60 else 10 if v<=150 else 4 if v<=500 else 0
def tier(s): return "A" if s>=70 else "B" if s>=50 else "C" if s>=30 else "D"
TLBL = {"A":"Desesperado · máxima oportunidad","B":"Oportunidad alta","C":"Oportunidad media","D":"Consolidado · baja prioridad"}

def main():
    if not C.MASTER.exists():
        print("No existe db/chile.csv todavía. Corré build_master.py primero."); return
    raw = list(csv.DictReader(open(C.MASTER, encoding="utf-8")))
    out = []
    for r in raw:
        rating = ff(r["review_rating"]); rev = ii(r["review_count"])
        sc = rep_pts(rating) + trac_pts(rev); tel = fmt_phone(r["phone"])
        tt = "cel" if tel.startswith("+56 9") else "fijo" if tel.startswith("+56 2") else ("otro" if tel else "")
        out.append({"reg": r.get("region",""), "comuna": r.get("comuna",""), "n": r["title"],
            "c": (r.get("category","") or "—").strip() or "—",
            "a": clean_addr(r["title"], r["address"])[:120],
            "t": tel, "tt": tt, "e": first_email(r.get("emails","")),
            "r": round(rating,1), "v": rev, "ti": tier(sc), "s": sc})
    meta = {"total": len(out), "con_tel": sum(1 for x in out if x["t"]),
            "tier_label": TLBL}
    OUT.write_text("window.DATA=" + json.dumps({"meta": meta, "rows": out},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"data.json -> {len(out)} negocios | con tel {meta['con_tel']}")
    tc = Counter(x["ti"] for x in out)
    for t in "ABCD": print(f"  Tier {t}: {tc[t]}")

if __name__ == "__main__":
    main()
