"""Reescritura profunda de /best-running-sneakers/ (18-nov-2026).

Datos de Amazon leídos el 18-nov-2026 (calificación y número de calificaciones). Drop: ficha de Amazon o
especificación del fabricante. Conserva CSS, cabecera y pie de la página original.
"""
import html
import json
import re
from pathlib import Path

PAG = Path(__file__).parent.parent / "docs" / "best-running-sneakers" / "index.html"
ORIG = Path(__file__).parent / "respaldos" / "best-running-sneakers.html"
TAG = "trendvortex00-20"
FECHA = "November 18, 2026"

if not ORIG.exists():
    ORIG.write_text(PAG.read_text(encoding="utf-8"), encoding="utf-8")
base = ORIG.read_text(encoding="utf-8")
css = re.search(r"<style>.*?</style>", base, re.S).group(0)
cabecera = re.search(r'<header id="site-header".*?</header>', base, re.S).group(0)
pie = re.search(r'<footer id="site-footer".*?</footer>', base, re.S).group(0)
pie = pie.replace("B0DNKBSWZ1", "B0DDF9L2BC")

P = [  # nombre, asin, mejor para, drop mm, estrellas, calificaciones, texto, saltar si
    ("Brooks Ghost 17", "B0DDF9L2BC", "Best overall for most runners", 12, 4.5, 3715,
     "The Ghost is the shoe running stores hand to people who say \"I just want something that works\". It is a neutral "
     "daily trainer with soft but not mushy foam, a stable heel and a smooth transition. The 17th version adds a little "
     "more foam (about 1 mm at the heel and 3 mm at the forefoot, per Brooks) without changing the familiar fit. The high "
     "12 mm drop suits heel strikers and runners coming back from calf or Achilles soreness.",
     "you land on your forefoot or want a fast, springy feel: the high drop and steady ride feel dull on tempo days."),
    ("ASICS Gel-Nimbus 27", "B0D42FG1WL", "Most cushioned for long runs and big mileage", 8, 4.6, 3054,
     "If your priority is protection on long runs, recovery days or hours on your feet, the Nimbus is the plush option. "
     "It has a thick stack of soft foam, a roomy knit upper and an 8 mm drop. It is heavier than the others here, which "
     "you notice when you try to run fast, but not when you run easy.",
     "you want a light shoe for speed work or you prefer to feel the ground."),
    ("Hoka Clifton 10", "B0D5FRX2W9", "Best light, cushioned option and for walking plus running", 8, 4.6, 2800,
     "The Clifton gives you a lot of cushion for its weight. Its rocker sole rolls you forward, which many runners and "
     "people who stand all day like. Hoka raised the drop in this version by about 3 mm (to 8 mm), so it feels more "
     "conventional than earlier Cliftons.",
     "you have a narrow foot that needs a locked-in heel, or you dislike the rocking sensation."),
    ("Nike Pegasus 41", "B0D2DHS2ZK", "Most versatile: easy days, faster days and the gym", 10, 4.6, 1381,
     "The Pegasus is firmer and livelier than the Ghost or Nimbus, so it handles faster runs better while staying "
     "comfortable for daily miles. It is also the one most people are happy to wear outside of running.",
     "you want maximum softness: it is the firmest ride in this list."),
    ("New Balance Fresh Foam X 880v15", "B0D2BQNNL6", "Best for wide feet and a lower drop", 6, 4.4, 950,
     "The 880 is a dependable, balanced daily trainer. Two details set it apart: it is sold in several widths, which "
     "helps runners whose feet hurt in standard shoes, and it has a 6 mm drop (per the Amazon listing), lower than the "
     "Ghost or Pegasus.",
     "you want a very soft, bouncy feel: the 880 is about consistency, not excitement."),
    ("Saucony Ride 18", "B0D31WQH7W", "Best balance of cushion and responsiveness", 8, 4.4, 683,
     "The Ride sits between soft and firm, with a stack of about 35/27 mm (8 mm drop). It is a good choice if the Ghost "
     "feels too plain and the Pegasus too firm.",
     "you need extra width; try the shoe on or order a wide version where available."),
    ("Socviis Air Cushion Running Shoes", "B0DNKBSWZ1", "Budget option for walking, gym and casual wear", None, 4.3, 1139,
     "This is a low-cost lifestyle sneaker with an air-cushion sole. Buyers like it for walking, light gym work and "
     "everyday wear. It is not built like the dedicated running shoes above, so do not expect the same cushioning or "
     "durability on regular runs.",
     "you run more than a couple of times a week: spend more on one of the running shoes above."),
]


def enlace(asin, texto, clase="product-title-link"):
    return (f'<a href="https://www.amazon.com/dp/{asin}?tag={TAG}" rel="nofollow sponsored" target="_blank" '
            f'class="{clase}">{texto}</a>')


def estrellas(e):
    return "★" * int(round(e)) + "☆" * (5 - int(round(e)))


filas = "\n".join(
    f"<tr><td><strong>{n}</strong></td><td>{b}</td><td style=white-space:nowrap>{f'{d} mm' if d else '—'}</td>"
    f"<td>{e:.1f}★ ({c:,})</td><td>{enlace(a, 'Check price', 'product-title-link')}</td></tr>"
    for n, a, b, d, e, c, *_ in P)

tarjetas = ""
for i, (n, a, b, d, e, c, t, s) in enumerate(P, 1):
    tarjetas += f"""
<div class="product-card" style="display:block">
  <div class="product-info">
    <div class="editors-badge">#{i} · {b}</div>
    <h3 style="margin:8px 0">{enlace(a, n)}</h3>
    <div class="stars-row"><span class="stars">{estrellas(e)}</span> <span class="rating-text">{e:.1f} out of 5</span>
      <span class="review-count">· {c:,} Amazon ratings as of {FECHA}</span></div>
    <p style="margin:12px 0">{t}</p>
    <p style="margin:0 0 12px"><strong>Drop:</strong> {f'{d} mm' if d else 'not published'}.
      <strong>Skip it if</strong> {s}</p>
    {enlace(a, 'Check current price on Amazon →', 'cta-btn product-cta')}
  </div>
</div>"""

FAQ = [
    ("What is the best running sneaker for beginners?",
     "A neutral, well-cushioned daily trainer is the safest start. In this guide that is the Brooks Ghost 17 or the "
     "Hoka Clifton 10. Avoid racing shoes and very minimal shoes until you run regularly without pain."),
    ("Are running shoes and jogging sneakers the same thing?",
     "Yes. Jogging is easy running, and the same daily trainers work for both. The difference that matters is not the "
     "name but cushioning, drop and fit for your foot."),
    ("What does heel-to-toe drop mean?",
     "Drop is the height difference between the heel and the forefoot, in millimeters. A higher drop (10 to 12 mm) "
     "takes load off the calves and Achilles and suits heel strikers. A lower drop (4 to 6 mm) loads the calves more and "
     "suits midfoot strikers. If you change drop by a lot, do it gradually."),
    ("Should I size up for running shoes?",
     "Many runners go half a size up from their casual shoes because feet swell during runs. Leave about a thumb's width "
     "between your longest toe and the end of the shoe, and check the brand's size chart before ordering."),
    ("How often should I replace running shoes?",
     "A common guideline is every 300 to 500 miles (about 500 to 800 km). Replace them sooner if the foam feels flat, the "
     "outsole is worn through or new aches appear after runs."),
    ("Do I need a stability shoe?",
     "Only if your feet roll inward a lot (overpronation) and that causes discomfort. Every shoe in this guide is neutral. "
     "Most runners do well in a neutral shoe; if you had injuries linked to overpronation, ask a specialist or try a "
     "stability version such as the Brooks Adrenaline or ASICS Gel-Kayano."),
]
faq_html = "\n".join(
    f'<div class="faq-item"><h3 class="faq-question">{q}</h3><div class="faq-answer"><p>{r}</p></div></div>' for q, r in FAQ)
ld_faq = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in FAQ]}
ld_lista = {"@context": "https://schema.org", "@type": "ItemList", "name": "Best running sneakers 2026",
            "itemListElement": [{"@type": "ListItem", "position": i, "name": p[0],
                                 "url": f"https://www.amazon.com/dp/{p[1]}"} for i, p in enumerate(P, 1)]}

pagina = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Best Running Sneakers 2026: 7 Picks for Every Runner | TrendVortex</title>
<meta name="description" content="Best running and jogging sneakers for 2026 compared: Brooks Ghost 17, ASICS Nimbus 27, Hoka Clifton 10, Nike Pegasus 41, New Balance 880v15 and Saucony Ride 18, with drop, ratings and who should skip each.">
<link rel="canonical" href="https://trendvortex.tech/best-running-sneakers/">
<link rel="icon" href="/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<script type="application/ld+json">{json.dumps(ld_faq, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(ld_lista, ensure_ascii=False)}</script>
{css}
</head>
<body>

{cabecera}

<div id="breadcrumb-bar">
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="https://trendvortex.tech/">Home</a><span class="sep">›</span><span>Sports</span><span class="sep">›</span><span class="current">Best running sneakers</span>
  </nav>
</div>

<section id="hero" role="region" aria-label="Hero">
  <div class="content-wrap">
    <span class="eyebrow-pill">Running</span>
    <h1>Best Running Sneakers in 2026: 7 Picks Compared</h1>
    <p class="subtitle">The right running shoe depends on how you run, not on which one is trending. We compared the most
    popular daily trainers by cushioning, heel-to-toe drop, fit and what owners report, and we say who should skip each one.</p>
    <div class="trust-badges">
      <span class="badge">✓ 7 shoes compared</span>
      <span class="badge">✓ Ratings checked {FECHA}</span>
      <span class="badge">✓ No paid placements</span>
    </div>
    <a href="#quick-picks" class="cta-btn">See the comparison ↓</a>
  </div>
</section>

<section class="section" id="quick-picks" aria-label="Quick comparison">
  <div class="content-wrap">
    <h2 class="section-title">Quick comparison</h2>
    <p>Ratings and rating counts are those shown on Amazon on {FECHA}; they change over time. Drop comes from the
    Amazon listing or the brand's published specification.</p>
    <div class="table-scroll" role="region" aria-label="Comparison table" tabindex="0">
      <table class="comparison-table">
        <thead><tr><th scope="col">Shoe</th><th scope="col">Best for</th><th scope="col">Drop</th><th scope="col">Amazon rating</th><th scope="col"></th></tr></thead>
        <tbody>
{filas}
        </tbody>
      </table>
    </div>
  </div>
</section>

<section class="section" aria-label="How to choose">
  <div class="content-wrap">
    <h2 class="section-title">How to choose a running shoe in 4 questions</h2>
    <div class="buying-guide-steps">
      <div class="step-item"><h3>1. How far and how often do you run?</h3>
        <p>For a few easy runs a week, any of the daily trainers here works. If you run long distances or more than four
        days a week, more cushioning (Gel-Nimbus 27, Clifton 10) protects your legs on tired days.</p></div>
      <div class="step-item"><h3>2. Do you land on your heel or midfoot?</h3>
        <p>Most recreational runners land on the heel. A higher drop (10 to 12 mm, like the Ghost 17 or Pegasus 41)
        reduces calf and Achilles load. Midfoot strikers often prefer 6 to 8 mm (880v15, Ride 18, Nimbus 27).</p></div>
      <div class="step-item"><h3>3. Soft or responsive?</h3>
        <p>Soft shoes feel great on easy days but can feel slow. Firmer, livelier shoes (Pegasus 41, Ride 18) feel
        better when you speed up. If you only want one pair, pick something in the middle.</p></div>
      <div class="step-item"><h3>4. What shape is your foot?</h3>
        <p>Fit matters more than any feature. If standard shoes squeeze your toes, look for a wide version (New Balance
        offers several widths). Leave about a thumb's width in front of your longest toe.</p></div>
    </div>
  </div>
</section>

<section class="section" id="top-pick" aria-label="The picks">
  <div class="content-wrap">
    <h2 class="section-title">The 7 picks in detail</h2>
    {tarjetas}
  </div>
</section>

<section class="section" aria-label="Running vs casual">
  <div class="content-wrap">
    <h2 class="section-title">Running shoes vs. fashion sneakers</h2>
    <p>A fashion sneaker can look like a running shoe and still feel fine for a walk. The difference shows up after a few
    kilometers: running shoes use foams designed to absorb repeated impact and to keep their shape for hundreds of miles,
    plus outsoles placed where runners wear them down. If you run regularly, buy a running shoe for running and keep the
    lifestyle pair for everything else.</p>
  </div>
</section>

<section class="section" aria-label="Frequently Asked Questions">
  <div class="content-wrap">
    <h2 class="section-title">Frequently asked questions</h2>
    <div class="faq-list">
{faq_html}
    </div>
    <p style="margin-top:24px;color:var(--text-secondary);font-size:.9rem">This guide is based on product specifications,
    the brands' published data and owner ratings; we did not lab-test these shoes. Questions or corrections:
    <a href="/contact.html">contact us</a>. How we work: <a href="/about.html">About TrendVortex</a>.</p>
  </div>
</section>

{pie}
</body>
</html>
"""
PAG.write_text(pagina, encoding="utf-8")
texto = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style|header|footer)[^>]*>.*?</\1>", " ", pagina)))
print("palabras:", len(texto.split()))
