"""Arreglos de confianza del sitio (18-nov-2026): favicon, /disclaimer/ y enlaces del pie en todas las páginas.

Idempotente: se puede correr varias veces sin duplicar nada.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DOCS = Path(__file__).parent / "docs"
LINKS = ('<nav class="tv-site-links" aria-label="Site" style="margin-top:.5rem;font-size:.8rem">'
         '<a href="/about.html">About</a> · <a href="/affiliate-disclosure.html">Affiliate Disclosure</a> · '
         '<a href="/contact.html">Contact</a> · <a href="/privacy-policy.html">Privacy Policy</a></nav>\n')
ICONO = '<link rel="icon" href="/favicon.ico">'

# 1. favicon
im = Image.new("RGBA", (64, 64), (10, 10, 15, 255))
d = ImageDraw.Draw(im)
d.rounded_rectangle([2, 2, 62, 62], 12, fill=(0, 212, 170, 255))
try:
    f = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 34)
except OSError:
    f = ImageFont.load_default()
w = d.textlength("TV", font=f)
d.text(((64 - w) / 2, 10), "TV", font=f, fill=(10, 10, 15, 255))
im.save(DOCS / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

# 2. /disclaimer/ -> aviso de afiliado (Google lo pedía y daba 404)
(DOCS / "disclaimer").mkdir(exist_ok=True)
(DOCS / "disclaimer" / "index.html").write_text(
    '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Disclaimer — TrendVortex</title>'
    '<link rel="canonical" href="https://trendvortex.tech/affiliate-disclosure.html">'
    '<meta name="robots" content="noindex,follow">'
    '<meta http-equiv="refresh" content="0; url=/affiliate-disclosure.html"></head>'
    '<body><p>Moved to <a href="/affiliate-disclosure.html">Affiliate Disclosure</a>.</p></body></html>',
    encoding="utf-8")

# 3. pie de página e icono en cada página
pies = iconos = 0
for p in DOCS.rglob("*.html"):
    t = p.read_text(encoding="utf-8", errors="ignore")
    nuevo = t
    if "tv-site-links" not in nuevo and "</footer>" in nuevo:
        i = nuevo.rfind("</footer>")
        nuevo = nuevo[:i] + LINKS + nuevo[i:]
        pies += 1
    if 'rel="icon"' not in nuevo and "</head>" in nuevo:
        nuevo = nuevo.replace("</head>", ICONO + "\n</head>", 1)
        iconos += 1
    if nuevo != t:
        p.write_text(nuevo, encoding="utf-8")
print(f"pies agregados: {pies} | iconos agregados: {iconos}")

# 4. sitemap: incluir about.html
sm = DOCS / "sitemap.xml"
s = sm.read_text(encoding="utf-8")
if "about.html" not in s:
    s = s.replace("</urlset>", "  <url><loc>https://trendvortex.tech/about.html</loc></url>\n</urlset>")
    sm.write_text(s, encoding="utf-8")
    print("about.html agregado al sitemap")
