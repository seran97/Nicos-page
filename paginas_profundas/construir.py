"""Constructor común de páginas profundas (usa CSS, cabecera y pie de la página original del sitio).

Cada página define un dict con: slug, title, desc, h1, sub, eyebrow, migas, nota_tabla, cols (cabeceras extra),
productos [dict(nombre, asin, para, extra[list], estrellas, n, texto, saltar)], pasos [(titulo, texto)],
secciones [(titulo, html)], faq [(pregunta, respuesta)], fecha.
"""
import html
import json
import re
from pathlib import Path

RAIZ = Path(__file__).parent.parent
TAG = "trendvortex00-20"


def _enlace(asin, texto, clase="product-title-link"):
    return (f'<a href="https://www.amazon.com/dp/{asin}?tag={TAG}" rel="nofollow sponsored" target="_blank" '
            f'class="{clase}">{texto}</a>')


def _est(e):
    return "★" * int(round(e)) + "☆" * (5 - int(round(e)))


def construir(c):
    pag = RAIZ / "docs" / c["slug"] / "index.html"
    resp = Path(__file__).parent / "respaldos" / f"{c['slug']}.html"
    resp.parent.mkdir(exist_ok=True)
    if not resp.exists():
        resp.write_text(pag.read_text(encoding="utf-8"), encoding="utf-8")
    base = resp.read_text(encoding="utf-8")
    if "<style>" not in base or 'id="site-header"' not in base or 'id="site-footer"' not in base:  # algunas páginas usan otra plantilla: tomar la de running como base visual
        base = (Path(__file__).parent / "respaldos" / "best-running-sneakers.html").read_text(encoding="utf-8")
    css = re.search(r"<style>.*?</style>", base, re.S).group(0)
    cab = re.search(r'<header id="site-header".*?</header>', base, re.S).group(0)
    pie = re.search(r'<footer id="site-footer".*?</footer>', base, re.S).group(0)
    pie = re.sub(r"/dp/[A-Z0-9]{10}\?", f"/dp/{c['productos'][0]['asin']}?", pie)
    f = c["fecha"]
    P = c["productos"]
    th = "".join(f'<th scope="col">{x}</th>' for x in c["cols"])
    filas = "\n".join(
        f"<tr><td><strong>{p['nombre']}</strong></td><td>{p['para']}</td>"
        + "".join(f"<td style=white-space:nowrap>{x}</td>" if len(str(x)) < 12 else f"<td>{x}</td>" for x in p["extra"])
        + f"<td style=white-space:nowrap>{p['estrellas']:.1f}★ ({p['n']:,})</td><td>{_enlace(p['asin'], 'Check price')}</td></tr>"
        for p in P)
    tarjetas = ""
    for i, p in enumerate(P, 1):
        datos = " · ".join(f"<strong>{k}:</strong> {v}" for k, v in zip(c["cols"], p["extra"]))
        tarjetas += f"""
<div class="product-card" style="display:block">
  <div class="product-info">
    <div class="editors-badge">#{i} · {p['para']}</div>
    <h3 style="margin:8px 0">{_enlace(p['asin'], p['nombre'])}</h3>
    <div class="stars-row"><span class="stars">{_est(p['estrellas'])}</span> <span class="rating-text">{p['estrellas']:.1f} out of 5</span>
      <span class="review-count">· {p['n']:,} Amazon ratings as of {f}</span></div>
    <p style="margin:12px 0">{p['texto']}</p>
    <p style="margin:0 0 12px">{datos}. <strong>Skip it if</strong> {p['saltar']}</p>
    {_enlace(p['asin'], 'Check current price on Amazon →', 'cta-btn product-cta')}
  </div>
</div>"""
    pasos = "\n".join(f'<div class="step-item"><h3>{i}. {t}</h3><p>{x}</p></div>' for i, (t, x) in enumerate(c["pasos"], 1))
    secciones = "\n".join(f"""<section class="section"><div class="content-wrap"><h2 class="section-title">{t}</h2>{x}</div></section>"""
                          for t, x in c.get("secciones", []))
    faq = "\n".join(f'<div class="faq-item"><h3 class="faq-question">{q}</h3><div class="faq-answer"><p>{r}</p></div></div>'
                    for q, r in c["faq"])
    ld1 = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in c["faq"]]}
    ld2 = {"@context": "https://schema.org", "@type": "ItemList", "name": c["h1"], "itemListElement": [
        {"@type": "ListItem", "position": i, "name": p["nombre"], "url": f"https://www.amazon.com/dp/{p['asin']}"}
        for i, p in enumerate(P, 1)]}
    url = f"https://trendvortex.tech/{c['slug']}/"
    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{c['title']}</title>
<meta name="description" content="{html.escape(c['desc'])}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<script type="application/ld+json">{json.dumps(ld1, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(ld2, ensure_ascii=False)}</script>
{css}
</head>
<body>
{cab}
<div id="breadcrumb-bar"><nav class="breadcrumb" aria-label="Breadcrumb"><a href="https://trendvortex.tech/">Home</a><span class="sep">›</span><span>{c['migas']}</span><span class="sep">›</span><span class="current">{c['h1'].split(':')[0]}</span></nav></div>
<section id="hero" role="region" aria-label="Hero"><div class="content-wrap">
  <span class="eyebrow-pill">{c['eyebrow']}</span>
  <h1>{c['h1']}</h1>
  <p class="subtitle">{c['sub']}</p>
  <div class="trust-badges"><span class="badge">✓ {len(P)} products compared</span><span class="badge">✓ Ratings checked {f}</span><span class="badge">✓ No paid placements</span></div>
  <a href="#quick-picks" class="cta-btn">See the comparison ↓</a>
</div></section>
<section class="section" id="quick-picks"><div class="content-wrap">
  <h2 class="section-title">Quick comparison</h2>
  <p>{c['nota_tabla']}</p>
  <div class="table-scroll" role="region" aria-label="Comparison table" tabindex="0"><table class="comparison-table">
  <thead><tr><th scope="col">Product</th><th scope="col">Best for</th>{th}<th scope="col">Amazon rating</th><th scope="col"></th></tr></thead>
  <tbody>
{filas}
  </tbody></table></div>
</div></section>
<section class="section"><div class="content-wrap"><h2 class="section-title">{c['titulo_pasos']}</h2><div class="buying-guide-steps">
{pasos}
</div></div></section>
<section class="section" id="top-pick"><div class="content-wrap"><h2 class="section-title">The {len(P)} picks in detail</h2>
{tarjetas}
</div></section>
{secciones}
<section class="section"><div class="content-wrap"><h2 class="section-title">Frequently asked questions</h2><div class="faq-list">
{faq}
</div>
<p style="margin-top:24px;color:var(--text-secondary);font-size:.9rem">{c['metodo']} Questions or corrections:
<a href="/contact.html">contact us</a>. How we work: <a href="/about.html">About TrendVortex</a>.</p>
</div></section>
{pie}
</body>
</html>
"""
    pag.write_text(out, encoding="utf-8")
    t = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style|header|footer)[^>]*>.*?</\1>", " ", out)))
    print(c["slug"], "palabras:", len(t.split()))


def fusionar(origen, destino):
    """Convierte /origen/ en redirección (meta refresh + canonical) hacia /destino/ y lo saca del sitemap."""
    p = RAIZ / "docs" / origen / "index.html"
    resp = Path(__file__).parent / "respaldos" / f"{origen}.html"
    if not resp.exists():
        resp.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    u = f"https://trendvortex.tech/{destino}/"
    p.write_text(f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Moved — TrendVortex</title>'
                 f'<link rel="canonical" href="{u}"><meta http-equiv="refresh" content="0; url=/{destino}/">'
                 f'<link rel="icon" href="/favicon.ico"></head><body><p>This guide moved to '
                 f'<a href="/{destino}/">{u}</a>.</p></body></html>', encoding="utf-8")
    sm = RAIZ / "docs" / "sitemap.xml"
    s = sm.read_text(encoding="utf-8")
    s = re.sub(r"\s*<url>\s*<loc>https://trendvortex\.tech/" + re.escape(origen) + r"/</loc>.*?</url>", "", s, flags=re.S)
    sm.write_text(s, encoding="utf-8")
    print("fusionada", origen, "->", destino)
