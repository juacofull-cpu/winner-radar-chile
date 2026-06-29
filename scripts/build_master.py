#!/usr/bin/env python3
"""
Reconstruye db/chile.csv desde los raw/<tarea>.csv añadiendo 'comuna' y 'region' al frente
y deduplicando global por place_id. Idempotente (se puede correr con scrapers en curso).
Fuente de verdad para panel/analysis/export. Escribe state/integrity.json.
"""
import csv, json, sys
import common as C

csv.field_size_limit(sys.maxsize)

def key(row, idx):
    pid = (row[idx["place_id"]].strip() if "place_id" in idx and idx["place_id"] < len(row) else "")
    if pid: return pid
    t = row[idx["title"]].strip().lower() if "title" in idx and idx["title"] < len(row) else ""
    a = row[idx["address"]].strip().lower() if "address" in idx and idx["address"] < len(row) else ""
    return f"{t}|{a}"

def tasks():
    out = []
    with open(C.COMUNAS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append((r["comuna"], r["region"], int(r["prioridad"])))
    out.sort(key=lambda t: (t[2], t[1], t[0]))
    return out

def main():
    seen = set(); total_raw = dup_cross = written = 0
    per = {}; header = None
    with open(C.MASTER, "w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo)
        for comuna, region, _ in tasks():
            f = C.RAW / f"{C.task_slug(comuna, region)}.csv"
            if not f.exists(): continue
            with open(f, newline="", encoding="utf-8") as fi:
                r = list(csv.reader(fi))
            if not r: continue
            h, rows = r[0], r[1:]
            idx = {c: i for i, c in enumerate(h)}
            if header is None:
                header = ["comuna", "region"] + h; w.writerow(header)
            for row in rows:
                if not row: continue
                total_raw += 1; k = key(row, idx)
                if k in seen: dup_cross += 1; continue
                seen.add(k); w.writerow([comuna, region] + row); written += 1
                per[(comuna, region)] = per.get((comuna, region), 0) + 1
    C.INTEG.write_text(json.dumps({"unicos": written, "crudos": total_raw,
        "dup_cross": dup_cross}, ensure_ascii=False), encoding="utf-8")
    print(f"BASE chile.csv -> {written} únicos | {total_raw} crudos | {dup_cross} dup cross-comuna")

if __name__ == "__main__":
    main()
