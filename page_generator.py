# -*- coding: utf-8 -*-
"""
page_generator.py — Fase 3: Generador de páginas HTML + sitemap
Genera una landing page SEO-optimizada por nicho validado.
"""

import os, re, json, csv
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SITE_URL   = os.getenv("SITE_URL", "https://tu-dominio.com")
AMAZON_TAG = os.getenv("AMAZON_TAG", "tu-tag-20")
DOCS_DIR   = Path("docs")
DOCS_DIR.mkdir(exist_ok=True)


def slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")


def generar_pagina(keyword: str, amazon: dict, trends: dict,
                   subreddit: str = "", amazon_cat: str = "") -> str:
    """
    Genera docs/best-{slug}/index.html
    Retorna el slug de la página creada.
    """
    kw_slug  = slug(keyword)
    anio     = datetime.now().year
    mes      = datetime.now().strftime("%B %Y")
    page_dir = DOCS_DIR / f"best-{kw_slug}"
    page_dir.mkdir(parents=True, exist_ok=True)

    page_url  = f"{SITE_URL}/best-{kw_slug}/"
    page_title = f"Best {keyword.title()} in {anio} — Honest Review"
    meta_desc  = (f"Reddit-validated: best {keyword} under $150. "
                  f"Real ratings, unbiased picks. Updated {mes}.")

    slope_txt = ("rising fast" if trends.get("slope", 0) > 10
                 else "steady" if trends.get("slope", 0) >= -5
                 else "declining")

    schema_product = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": amazon["titulo"],
        "description": f"Top-rated {keyword} picked from Reddit buying-intent analysis.",
        "image": amazon["imagen_url"],
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": str(amazon["rating"]),
            "reviewCount": str(amazon["reviews"]),
            "bestRating": "5",
            "worstRating": "1",
        },
        "offers": {
            "@type": "Offer",
            "price": str(amazon["precio"]),
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "url": amazon["affiliate_url"],
        }
    }

    schema_faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"What is the best {keyword}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (f"Based on Reddit community feedback and Amazon ratings, "
                             f"the {amazon['titulo']} ({amazon['rating']}★, "
                             f"{amazon['reviews']:,} reviews) stands out at "
                             f"${amazon['precio']:.2f}.")
                }
            },
            {
                "@type": "Question",
                "name": f"Is {keyword} worth buying?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (f"With {amazon['reviews']:,} verified reviews averaging "
                             f"{amazon['rating']}★ and a price of ${amazon['precio']:.2f}, "
                             f"it sits in the $30–$150 sweet spot that Reddit buyers trust.")
                }
            },
            {
                "@type": "Question",
                "name": f"Where to buy the best {keyword}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": (f"Amazon offers the best combination of price protection, "
                             f"easy returns, and Prime shipping for {keyword}.")
                }
            }
        ]
    }

    schema_breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1,
             "name": "Home", "item": SITE_URL},
            {"@type": "ListItem", "position": 2,
             "name": page_title, "item": page_url},
        ]
    }

    stars_filled = "★" * int(amazon["rating"])
    stars_empty  = "☆" * (5 - int(amazon["rating"]))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title}</title>
  <meta name="description" content="{meta_desc}">
  <link rel="canonical" href="{page_url}">

  <!-- Open Graph -->
  <meta property="og:title" content="{page_title}">
  <meta property="og:description" content="{meta_desc}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{page_url}">
  <meta property="og:image" content="{amazon['imagen_url']}">

  <!-- Schema.org -->
  <script type="application/ld+json">{json.dumps(schema_product)}</script>
  <script type="application/ld+json">{json.dumps(schema_faq)}</script>
  <script type="application/ld+json">{json.dumps(schema_breadcrumb)}</script>

  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          line-height:1.7;color:#222;max-width:820px;margin:0 auto;padding:16px 20px}}
    nav{{font-size:.9rem;margin-bottom:1.5rem;color:#888}}
    nav a{{color:#0066cc;text-decoration:none}}
    h1{{font-size:1.85rem;line-height:1.2;margin-bottom:.4rem;color:#111}}
    h2{{font-size:1.2rem;margin:2rem 0 .6rem;color:#333;border-bottom:2px solid #f0f0f0;padding-bottom:.3rem}}
    h3{{font-size:1rem;margin:1.2rem 0 .4rem;color:#444}}
    p{{margin-bottom:.9rem}}
    .badge{{display:inline-block;background:#f0f7ff;border:1px solid #c0d8f0;
             border-radius:4px;padding:2px 9px;font-size:.78rem;color:#2255aa;margin:.2rem .2rem 0 0}}
    .product-card{{display:flex;gap:18px;background:#fff;border:1px solid #ddd;
                    border-radius:10px;padding:18px;margin:1.5rem 0;
                    box-shadow:0 2px 8px rgba(0,0,0,.07)}}
    .product-card img{{width:130px;height:130px;object-fit:contain;flex-shrink:0;
                        border-radius:6px;background:#f9f9f9}}
    .product-info{{flex:1}}
    .product-name{{font-weight:600;font-size:1rem;margin-bottom:.5rem;color:#111}}
    .stars{{color:#e77600;font-size:1.05rem;letter-spacing:1px}}
    .review-count{{font-size:.85rem;color:#666;margin-left:4px}}
    .price{{font-size:1.5rem;font-weight:700;color:#0a7b3e;margin:.5rem 0}}
    .cta-btn{{display:inline-block;background:#ff9900;color:#111;
               padding:11px 24px;border-radius:6px;text-decoration:none;
               font-weight:700;font-size:.95rem;margin-top:8px;
               transition:background .15s}}
    .cta-btn:hover{{background:#e68a00}}
    .reddit-signal{{background:#fff8f0;border-left:4px solid #ff4500;
                     padding:12px 16px;margin:1.5rem 0;border-radius:0 8px 8px 0;
                     font-size:.95rem}}
    .trend-bar{{display:inline-block;background:#e8f5e9;color:#2e7d32;
                 border-radius:4px;padding:2px 8px;font-size:.82rem;font-weight:600}}
    table{{width:100%;border-collapse:collapse;margin:1rem 0;font-size:.93rem}}
    th,td{{padding:9px 12px;text-align:left;border-bottom:1px solid #eee}}
    th{{background:#f7f7f7;font-weight:600;color:#444}}
    tr:last-child td{{border-bottom:none}}
    .faq-item{{margin-bottom:1.2rem}}
    .faq-q{{font-weight:600;color:#222;margin-bottom:.3rem}}
    footer{{margin-top:3rem;padding:1.2rem 0;border-top:1px solid #eee;
             font-size:.8rem;color:#999}}
    @media(max-width:600px){{
      .product-card{{flex-direction:column}}
      .product-card img{{width:100%;height:180px}}
    }}
  </style>
</head>
<body>

<nav><a href="/">Home</a> › {keyword.title()}</nav>

<article itemscope itemtype="https://schema.org/Article">

  <h1 itemprop="headline">{page_title}</h1>
  <p>
    <span class="badge">Reddit-validated</span>
    <span class="badge">Updated {mes}</span>
    <span class="badge">Affiliate disclosure</span>
    {f'<span class="badge">{amazon_cat}</span>' if amazon_cat else ''}
  </p>

  <div class="reddit-signal">
    <strong>Why this page exists:</strong> Reddit's
    {f'r/{subreddit} ' if subreddit else 'community '}flagged high buying intent
    for <em>{keyword}</em>.
    Google Trends confirms
    <span class="trend-bar">{trends.get("hits_reciente", "—")}/100 interest</span>
    with a {"+" if trends.get("slope", 0) >= 0 else ""}{trends.get("slope", "—")} point
    slope — this niche is <strong>{slope_txt}</strong>.
  </div>

  <h2>Our Top Pick for {keyword.title()}</h2>

  <div class="product-card">
    <img src="{amazon['imagen_url']}" alt="{amazon['titulo']}" loading="lazy">
    <div class="product-info">
      <p class="product-name">{amazon['titulo']}</p>
      <p>
        <span class="stars">{stars_filled}{stars_empty}</span>
        <span class="review-count">{amazon['rating']} ({amazon['reviews']:,} reviews)</span>
      </p>
      <p class="price">${amazon['precio']:.2f}</p>
      <a class="cta-btn" href="{amazon['affiliate_url']}"
         rel="nofollow sponsored" target="_blank">
        Check Price on Amazon →
      </a>
    </div>
  </div>

  <h2>Why Reddit Users Recommend It</h2>
  <p>Across multiple threads in buying-intent communities, users consistently mention
  <strong>{keyword}</strong> as a real pain point with clear purchasing signals.
  The product above emerged as the top recommendation based on the best
  price-to-quality ratio in the $30–$150 range.</p>

  <h2>Quick Comparison: What to Look For</h2>
  <table>
    <tr><th>Factor</th><th>What Reddit Says</th><th>Our Pick</th></tr>
    <tr>
      <td>Price range</td>
      <td>$30–$150 sweet spot</td>
      <td>${amazon['precio']:.0f} ✓</td>
    </tr>
    <tr>
      <td>Rating</td>
      <td>4.0★ minimum</td>
      <td>{amazon['rating']}★ ✓</td>
    </tr>
    <tr>
      <td>Reviews</td>
      <td>Enough to trust</td>
      <td>{amazon['reviews']:,} reviews ✓</td>
    </tr>
    <tr>
      <td>Trend signal</td>
      <td>Rising or steady</td>
      <td>{trends.get("hits_reciente", "—")}/100 ({slope_txt}) ✓</td>
    </tr>
  </table>

  <h2>Frequently Asked Questions</h2>

  <div class="faq-item">
    <p class="faq-q">What is the best {keyword}?</p>
    <p>Based on Reddit community feedback and Amazon ratings, the
    <strong>{amazon['titulo']}</strong> ({amazon['rating']}★, {amazon['reviews']:,} reviews)
    leads in the ${amazon['precio']:.0f} price range.</p>
  </div>

  <div class="faq-item">
    <p class="faq-q">Is {keyword} worth buying?</p>
    <p>With {amazon['reviews']:,} verified Amazon reviews averaging {amazon['rating']}★
    at ${amazon['precio']:.2f}, it sits squarely in the value sweet spot this
    community trusts.</p>
  </div>

  <div class="faq-item">
    <p class="faq-q">Where to buy {keyword}?</p>
    <p>Amazon offers the best combination of price protection, easy returns, and
    Prime shipping.
    <a href="{amazon['affiliate_url']}" rel="nofollow sponsored">Check current price here</a>.
    </p>
  </div>

</article>

<footer>
  <p><strong>Affiliate disclosure:</strong> This page contains affiliate links.
  We may earn a small commission at no extra cost to you if you purchase through our links.</p>
  <p>Last updated: {datetime.now().strftime("%Y-%m-%d")}</p>
</footer>

</body>
</html>"""

    (page_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"  [PAGE] docs/best-{kw_slug}/index.html")
    return kw_slug


def actualizar_sitemap():
    """Regenera docs/sitemap.xml con todas las páginas existentes."""
    pages = sorted(DOCS_DIR.glob("*/index.html"))
    # excluir el index raíz
    pages = [p for p in pages if p.parent != DOCS_DIR]

    urls = "\n".join(
        f'  <url>'
        f'<loc>{SITE_URL}/{p.parent.name}/</loc>'
        f'<changefreq>weekly</changefreq>'
        f'<priority>0.8</priority>'
        f'</url>'
        for p in pages
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{SITE_URL}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
{urls}
</urlset>"""
    (DOCS_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"  [SITEMAP] {len(pages)} páginas indexadas")


def actualizar_index_html():
    """
    Inyecta las páginas publicadas en el catálogo existente (docs/index.html).
    Busca el marcador <!-- PRODUCTS_GRID --> y lo reemplaza con tarjetas de producto.
    Si el marcador no existe, NO sobreescribe el index.html (preserva el diseño).
    """
    pages = sorted(DOCS_DIR.glob("*/index.html"))
    pages = [p for p in pages if p.parent != DOCS_DIR]

    index_path = DOCS_DIR / "index.html"
    if not index_path.exists():
        print(f"  [INDEX] index.html no encontrado — saltando")
        return

    current = index_path.read_text(encoding="utf-8")

    # Generar tarjetas de producto
    cards = ""
    for p in pages:
        slug  = p.parent.name
        nombre = slug.replace("best-", "").replace("-", " ").title()
        cards += (
            f'<a href="/{slug}/" class="product-card">'
            f'<div class="pc-img"></div>'
            f'<div class="pc-info">'
            f'<h3 class="pc-title">Best {nombre}</h3>'
            f'<p class="pc-sub">Top picks · Reddit validated</p>'
            f'<span class="pc-cta">See Recommendations →</span>'
            f'</div></a>\n'
        )

    marker = "<!-- PRODUCTS_GRID -->"
    end_marker = "<!-- /PRODUCTS_GRID -->"

    if marker in current and end_marker in current:
        # Reemplazar solo el contenido entre marcadores
        start_idx = current.index(marker) + len(marker)
        end_idx   = current.index(end_marker)
        updated   = current[:start_idx] + "\n" + cards + current[end_idx:]
        index_path.write_text(updated, encoding="utf-8")
        print(f"  [INDEX] Homepage actualizada ({len(pages)} páginas)")
    else:
        # El index no tiene marcadores — NO sobreescribir (preservar diseño)
        print(f"  [INDEX] Marcadores no encontrados — index.html preservado ({len(pages)} páginas disponibles)")


if __name__ == "__main__":
    # Test: genera una página de ejemplo sin Amazon real
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    test_amazon = {
        "asin": "B08N5WRWNW",
        "titulo": "Sous Vide Cooker Precision Immersion Circulator 1000W",
        "precio": 79.99, "rating": 4.5, "reviews": 3241,
        "imagen_url": "https://m.media-amazon.com/images/I/example.jpg",
        "affiliate_url": f"https://amazon.com/dp/B08N5WRWNW?tag={AMAZON_TAG}",
    }
    test_trends = {"hits_max": 85, "hits_reciente": 72.5, "slope": 14.2, "trending": True}
    s = generar_pagina("sous vide cooker", test_amazon, test_trends,
                       subreddit="sousvide", amazon_cat="Kitchen & Dining")
    actualizar_sitemap()
    actualizar_index_html()
    print(f"\nPagina generada: docs/best-{s}/index.html")
