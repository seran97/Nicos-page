import re, json, html
from pathlib import Path
from collections import Counter, defaultdict
D = Path("docs")
sm = re.findall(r"<loc>https://trendvortex\.tech/([^<]*)</loc>", open("docs/sitemap.xml", encoding="utf-8").read())
slugs = [s.strip("/") for s in sm if s.strip("/")]
existing = {p.name for p in D.iterdir() if p.is_dir()}
existing_files = {p.name for p in D.iterdir() if p.is_file()}
prob = defaultdict(list); titles = defaultdict(list); descs = defaultdict(list); words = {}
HUBS={"best-kitchen-dining","best-gaming-gear","best-automotive","best-pet-supplies","best-sports-outdoors","best-fashion","best-home-improvement","best-beauty","best-baby-products"}
def tipo(s,t):
    if "badge-guide" in t: return "guia"
    if s in HUBS: return "hub"
    if "-vs-" in s: return "vs"
    return "resena"
tipos=Counter()
for s in slugs:
    t = (D/s/"index.html").read_text(encoding="utf-8", errors="replace")
    k=tipo(s,t); tipos[k]+=1
    ti = re.search(r"<title>([^<]*)</title>", t); ti = html.unescape(ti.group(1)).strip() if ti else ""
    de = re.search(r'<meta name="description" content="([^"]*)"', t); de = html.unescape(de.group(1)) if de else ""
    titles[ti].append(s); descs[de].append(s)
    if not ti: prob["sin title"].append(s)
    elif len(ti) > 70: prob["title > 70 car."].append(s)
    if not de: prob["sin meta description"].append(s)
    elif not (70 <= len(de) <= 165): prob["description fuera de 70-165"].append(s)
    can = re.search(r'<link rel="canonical" href="([^"]*)"', t)
    if not can: prob["sin canonical"].append(s)
    elif can.group(1).rstrip("/") != f"https://trendvortex.tech/{s}": prob["canonical apunta a otra URL"].append(s)
    h1 = len(re.findall(r"<h1[\s>]", t))
    if h1 != 1: prob[f"h1 = {h1}"].append(s)
    if 'name="viewport"' not in t: prob["sin viewport"].append(s)
    if not re.search(r'<html[^>]*lang=', t): prob["sin lang"].append(s)
    for b in re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', t, re.S):
        try: json.loads(b)
        except Exception: prob["JSON-LD inválido"].append(s); break
    aff = re.findall(r'<a[^>]+href="(https?://(?:www\.)?(?:amazon\.|amzn\.|ebay\.|aliexpress)[^"]*)"[^>]*>', t)
    tags = re.findall(r'<a[^>]+href="https?://(?:www\.)?(?:amazon\.|amzn\.|ebay\.|aliexpress)[^"]*"[^>]*>', t)
    if any('sponsored' not in x for x in tags): prob["enlace afiliado sin rel=sponsored"].append(s)
    if aff and not re.search(r"affiliate|commission|Amazon Associate", t, re.I): prob["afiliado sin aviso"].append(s)
    if k=="guia" and aff: prob["guía con enlace de afiliado"].append(s)
    imgs = re.findall(r"<img[^>]*>", t)
    if any('alt="' not in i or 'alt=""' in i for i in imgs): prob["img sin alt"].append(s)
    if re.search(r'placeholder|via\.placeholder|no-image', t, re.I): prob["imagen placeholder"].append(s)
    for h in re.findall(r'href="(?:https://trendvortex\.tech)?/([^"#?]*)"', t):
        h = h.strip("/")
        if h and h.split("/")[0] not in existing and h not in existing_files: prob["enlace interno roto"].append(f"{s} -> /{h}"); 
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    body = re.sub(r"<header.*?</header>|<footer.*?</footer>|<nav.*?</nav>", " ", body, flags=re.S)
    w = len(re.sub(r"<[^>]+>", " ", body).split()); words[s]=(k,w)
for ti, ss in titles.items():
    if len(ss) > 1: prob["title duplicado"].append(f"{len(ss)}x {ti[:60]}")
for de, ss in descs.items():
    if len(ss) > 1 and de: prob["description duplicada"].append(f"{len(ss)}x {de[:60]}")
print("páginas:", len(slugs), dict(tipos))
for k, v in sorted(prob.items(), key=lambda x: -len(x[1])):
    print(f"{len(v):4}  {k}   ej: {v[:3]}")
import statistics as st
for k in ("guia","hub","vs","resena"):
    ws=[w for kk,w in words.values() if kk==k]
    if ws: print(k, "palabras min/med/max", min(ws), int(st.median(ws)), max(ws), "| <400:", sum(w<400 for w in ws))
json.dump({k: v for k, v in prob.items()}, open("auditoria_2026-10-18.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
