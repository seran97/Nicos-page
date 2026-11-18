"""Mide palabras de cada página del sitemap y la clasifica (para poda)."""
import re, html, json
from pathlib import Path
DOCS = Path(__file__).parent / "docs"
urls = re.findall(r"<loc>https://trendvortex\.tech/([^<]*)</loc>", (DOCS / "sitemap.xml").read_text(encoding="utf-8"))
filas = []
for u in urls:
    p = DOCS / u / "index.html" if (not u or u.endswith("/")) else DOCS / u
    if not p.exists():
        filas.append({"url": u, "palabras": -1}); continue
    t = p.read_text(encoding="utf-8", errors="ignore")
    b = re.sub(r"(?s)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", t)
    w = len(html.unescape(re.sub(r"<[^>]+>", " ", b)).split())
    titulo = (re.findall(r"<title>(.*?)</title>", t, re.S) or [""])[0].strip()
    filas.append({"url": u, "palabras": w, "titulo": titulo,
                  "noindex": "noindex" in t[:5000], "tipo": "info" if not u.startswith(("best-", "christmas")) else u.split("-")[0]})
json.dump(filas, open("medicion_paginas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
import collections
print("total", len(filas), "| faltan", sum(f["palabras"] < 0 for f in filas))
for a, b in [(0, 400), (400, 500), (500, 600), (600, 800), (800, 1200), (1200, 99999)]:
    print(f"{a}-{b}:", sum(a <= f["palabras"] < b for f in filas))
print(collections.Counter(f.get("tipo") for f in filas))
print("titulos con Parts/Accessories:", sum(bool(re.search(r"\b(Parts|Accessories|Replacement)\b", f.get("titulo",""))) for f in filas))
