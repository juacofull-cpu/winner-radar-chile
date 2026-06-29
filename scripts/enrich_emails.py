#!/usr/bin/env python3
"""
FASE 2 — Enriquecimiento de emails (rápido, sin navegador).
Lee db/chile.csv, toma los negocios CON sitio web y SIN email, visita cada web con HTTP plano
(concurrente) y extrae correos del HTML / mailto. Escribe los emails de vuelta a chile.csv.

Aprovecha la potencia del PC: es I/O-bound, así que corre cientos de webs en paralelo
(EMAIL_WORKERS). No martilla a Google (visita dominios variados) → sin riesgo de baneo.
Reanudable vía db/email_cache.json. Idempotente.

Uso:   python scripts/enrich_emails.py        (EMAIL_WORKERS=80 por defecto)
       EMAIL_WORKERS=150 python scripts/enrich_emails.py   (PC potente)
"""
import csv, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import common as C

csv.field_size_limit(sys.maxsize)
WORKERS = int(os.getenv("EMAIL_WORKERS", "80"))
TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "8"))
MAXBYTES = 600_000
CACHE = C.DB / "email_cache.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
CONTACT_PATHS = ["", "/contacto", "/contact", "/contactanos", "/contacto.html"]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
BAD_EXT = (".gif", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".css", ".js", ".ico")
BAD_DOM = ("sentry.io", "wixpress.com", "godaddy.com", "squarespace.com", "getjusto.com",
           "googleapis.com", "schema.org", "example.com", "dominio.com", "domain.com",
           "sentry-next.wixpress.com", "wix.com", "cloudflare.com", "w3.org")
PLACEHOLDERS = {"usuario@dominio.com", "email@dominio.com", "tucorreo@dominio.com",
                "nombre@dominio.com", "info@tudominio.cl", "correo@correo.com"}

def clean(found):
    out = []
    for e in found:
        e = e.strip().strip(".").lower()
        if not EMAIL_RE.fullmatch(e): continue
        if e.endswith(BAD_EXT) or e in PLACEHOLDERS: continue
        dom = e.split("@", 1)[1]
        if any(dom == d or dom.endswith("." + d) for d in BAD_DOM): continue
        loc = e.split("@", 1)[0]
        if len(loc) >= 24 and re.fullmatch(r"[0-9a-f]+", loc): continue   # tracking hash
        if e not in out: out.append(e)
    return out

def fetch(url):
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True, stream=True)
        ct = r.headers.get("content-type", "")
        if "html" not in ct and "text" not in ct: return ""
        buf = b""
        for chunk in r.iter_content(8192):
            buf += chunk
            if len(buf) >= MAXBYTES: break
        return buf.decode(r.encoding or "utf-8", errors="ignore")
    except Exception:
        return ""

def emails_for(website):
    if not website.startswith(("http://", "https://")):
        website = "https://" + website
    base = website.rstrip("/")
    found = []
    for path in CONTACT_PATHS:
        html = fetch(base + path)
        if not html: continue
        # mailto: primero (más confiable)
        found += re.findall(r"mailto:([^\"'?>\s]+)", html)
        found += EMAIL_RE.findall(html)
        cl = clean(found)
        if cl: return cl          # corta apenas encuentra algo válido
    return clean(found)

def main():
    if not C.MASTER.exists():
        print("No existe db/chile.csv. Corré build_master.py primero."); return
    rows = list(csv.DictReader(open(C.MASTER, encoding="utf-8")))
    fields = rows[0].keys() if rows else []
    if "emails" not in fields:
        print("La base no tiene columna 'emails'."); return
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    targets = []
    for r in rows:
        web = (r.get("website") or "").strip()
        if web and not (r.get("emails") or "").strip() and web not in cache:
            targets.append(web)
    targets = list(dict.fromkeys(targets))   # únicos, preserva orden
    print(f"Webs a visitar: {len(targets)}  (workers={WORKERS}, ya en caché={len(cache)})")

    done = 0; hits = 0; t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(emails_for, w): w for w in targets}
        for fut in as_completed(futs):
            web = futs[fut]
            try: em = fut.result()
            except Exception: em = []
            cache[web] = em; done += 1
            if em: hits += 1
            if done % 100 == 0:
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                r = done / max(time.time() - t0, 1)
                print(f"  {done}/{len(targets)} · {hits} con email · {r:.0f}/s")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    # aplicar a la base y reescribir chile.csv
    applied = 0
    for r in rows:
        web = (r.get("website") or "").strip()
        if web and not (r.get("emails") or "").strip() and cache.get(web):
            r["emails"] = ", ".join(cache[web]); applied += 1
    tmp = C.MASTER.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fields)); w.writeheader(); w.writerows(rows)
    tmp.replace(C.MASTER)
    con_mail = sum(1 for r in rows if (r.get("emails") or "").strip())
    print(f"\n✅ Enriquecidos {applied} negocios con email nuevo.")
    print(f"   Base ahora: {con_mail}/{len(rows)} con email ({100*con_mail//max(len(rows),1)}%).")

if __name__ == "__main__":
    main()
