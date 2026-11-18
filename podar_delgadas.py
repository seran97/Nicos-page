"""Poda 18-nov-2026: fichas best-* que Google descubrió y no rastrea, con < 600 palabras.

noindex,follow + fuera del sitemap + fuera de la cola de GSC. Lista guardada en poda_2026-11-18.json (reversible).
"""
import json, re
from pathlib import Path
R = Path(__file__).parent
DOCS = R / "docs"
L = json.load(open(R / "gsc_listas_2026-11-18.json"))
M = {f["url"].strip("/"): f for f in json.load(open(R / "medicion_paginas.json", encoding="utf-8"))}
k = lambda u: u.replace("https://trendvortex.tech/", "").strip("/")
poda = sorted(x for x in (k(u) for u in L["descubierta"]) if x in M and M[x]["tipo"] == "best" and M[x]["palabras"] < 600)
json.dump(poda, open(R / "poda_2026-11-18.json", "w", encoding="utf-8"), indent=1)
hechas = 0
for x in poda:
    p = DOCS / x / "index.html"
    t = p.read_text(encoding="utf-8")
    if 'name="robots"' in t:
        t = re.sub(r'<meta name="robots" content="[^"]*">', '<meta name="robots" content="noindex,follow">', t, 1)
    else:
        t = t.replace("</head>", '<meta name="robots" content="noindex,follow">\n</head>', 1)
    p.write_text(t, encoding="utf-8"); hechas += 1
sm = DOCS / "sitemap.xml"; s = sm.read_text(encoding="utf-8"); antes = s.count("<url>")
for x in poda:
    s = re.sub(r"\s*<url>\s*<loc>https://trendvortex\.tech/" + re.escape(x) + r"/</loc>.*?</url>", "", s, flags=re.S)
sm.write_text(s, encoding="utf-8")
cola = json.load(open(R / "gsc_cola.json", encoding="utf-8"))
quitadas = len(cola["pendientes"])
cola["pendientes"] = [u for u in cola["pendientes"] if k(u) not in set(poda)]
quitadas -= len(cola["pendientes"])
json.dump(cola, open(R / "gsc_cola.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"noindex: {hechas} | sitemap {antes} -> {s.count('<url>')} | quitadas de la cola GSC: {quitadas} | quedan en cola: {len(cola['pendientes'])}")
