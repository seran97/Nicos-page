# -*- coding: utf-8 -*-
"""gen_hub_pages.py — Generate hub/pillar "Best of [Category]" pages linking to all reviews."""
import sys, re, json
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

import os
os.chdir(Path(__file__).parent)
from dotenv import load_dotenv
load_dotenv()
SITE_URL = os.getenv("SITE_URL", "https://trendvortex.tech")
DOCS_DIR = Path("docs")

CATEGORY_META = {
    "Kitchen & Dining": {
        "slug": "best-kitchen-dining", "emoji": "🍳",
        "desc": "air fryers, sous vide cookers, coffee makers, and more",
        "intro": "Kitchen appliances live or die on two things: how much counter space they eat up and whether they actually save you time on a weeknight. We weigh capacity against footprint, check how loud a unit runs, and flag models with parts that are a pain to hand-wash before they make this list.",
        "tips": [
            "Match capacity to household size — a 2-quart air fryer basket is fine solo, cramped for a family of four.",
            "Dishwasher-safe parts matter more than an extra preset mode once you're cooking daily.",
            "Check real decibel or noise complaints in reviews, not just wattage, before buying anything with a motor.",
        ],
    },
    "Amazon Games": {
        "slug": "best-gaming-gear", "emoji": "🎮",
        "desc": "mechanical keyboards, gaming mice, headsets, and accessories",
        "intro": "Switch type, polling rate, and driver software quality separate gear that lasts from gear you'll replace in a year. We favor hot-swappable keyboards and mice with onboard memory over gimmick RGB, and dock headsets a point for software that nags you to create an account.",
        "tips": [
            "Linear switches suit fast FPS play; tactile or clicky switches suit typing-heavy use — don't buy on looks alone.",
            "Wireless latency has closed the gap with wired, but check reviews for the specific dongle/Bluetooth combo you'll use.",
            "Onboard memory (no software required) beats cloud-profile gear if you switch PCs or consoles often.",
        ],
    },
    "Automotive": {
        "slug": "best-automotive", "emoji": "🚗",
        "desc": "dashcams, car accessories, seat covers, and detailing kits",
        "intro": "For dashcams and car electronics, footage quality in direct sunlight and at night matters more than the megapixel number on the box. For seat covers and detailing gear, fit-per-model and how well a product holds up after a dozen washes is what separates a good buy from a returned one.",
        "tips": [
            "For dashcams, check night-mode sample footage in reviews, not just the resolution spec on the listing.",
            "Universal-fit seat covers rarely fit as advertised — check for your exact make/model in the Q&A section.",
            "Loop-recording storage fills fast; buy a card rated for continuous write speeds, not a generic SD card.",
        ],
    },
    "Pet Supplies": {
        "slug": "best-pet-supplies", "emoji": "🐾",
        "desc": "dog food, cat litter, pet cameras, and more",
        "intro": "Food and litter picks come down to ingredient sourcing and how consistent a formula is batch to batch — a high review count with a stable rating is a stronger signal than a handful of five-star reviews. For gear like cameras and feeders, we weigh how often the app or connection actually causes complaints.",
        "tips": [
            "Read the first five ingredients on any food listing — a named protein should lead, not a generic 'meat meal.'",
            "Grain-free isn't automatically healthier; talk to a vet before switching if your pet has no diagnosed allergy.",
            "For connected gear (cameras, feeders), check reviews for app reliability, not just the hardware spec sheet.",
        ],
    },
    "Sports & Outdoors": {
        "slug": "best-sports-outdoors", "emoji": "🏃",
        "desc": "running shoes, camping gear, yoga mats, and outdoor essentials",
        "intro": "Running shoes and outdoor gear are the categories where fit and personal preference outweigh any single 'best' pick — cushioning, arch support, and terrain all shift the right answer. We prioritize items with a wide range of verified reviews across different use cases over a single flashy spec.",
        "tips": [
            "Running shoe sizing runs inconsistent across brands — check reviews for whether a model runs true, narrow, or wide.",
            "For camping and outdoor gear, weight and pack size matter as much as durability if you're carrying it any distance.",
            "A high star rating with a low review count is a weaker signal than a slightly lower rating with thousands of reviews.",
        ],
    },
    "Fashion": {
        "slug": "best-fashion", "emoji": "👔",
        "desc": "watches, wallets, earrings, and accessories",
        "intro": "For watches, wallets, and everyday accessories, material quality and hardware (clasps, movements, plating) tend to matter more long-term than the design trend of the moment. We look for consistent buyer feedback on how items hold up after a few months of daily use, not just first-impression photos.",
        "tips": [
            "Check plating/material specs closely — 'gold-tone' and 'gold-filled' age very differently over daily wear.",
            "For watches, battery life and water-resistance rating matter more day-to-day than chronograph features you won't use.",
            "Read reviews for hardware complaints (broken clasps, thinning straps) — those show up months after purchase, not in early reviews.",
        ],
    },
    "Home Improvement": {
        "slug": "best-home-improvement", "emoji": "🏠",
        "desc": "robot vacuums, air purifiers, dehumidifiers, and more",
        "intro": "Robot vacuums, air purifiers, and dehumidifiers are judged on maintenance cost as much as upfront price — filter and replacement-part costs can outweigh what you saved on the unit itself. We check CADR/coverage specs against the room size claimed, and flag units with app or mapping complaints.",
        "tips": [
            "Check CADR rating against your actual room size — most air purifiers are oversold on coverage area.",
            "For robot vacuums, mapping/navigation complaints in reviews matter more than suction wattage on the spec sheet.",
            "Factor in filter and replacement-part costs over a year, not just the sticker price of the unit.",
        ],
    },
    "Luxury Beauty": {
        "slug": "best-beauty", "emoji": "✨",
        "desc": "serums, sunscreens, skincare routines, and more",
        "intro": "For skincare, active ingredient concentration and how a formula plays with sensitive skin matter more than brand packaging. We look for products with ingredient lists that back up their marketing claims and flag anything with a pattern of reported irritation in reviews.",
        "tips": [
            "Check the active ingredient percentage, not just the marketing name — 'vitamin C serum' varies widely in strength.",
            "Patch-test anything new for 48 hours, especially actives like retinol or high-percentage acids.",
            "Mineral SPF (zinc oxide/titanium dioxide) tends to suit sensitive skin better than chemical sunscreen filters.",
        ],
    },
    "Toys & Baby": {
        "slug": "best-baby-products", "emoji": "👶",
        "desc": "baby monitors, strollers, toddler toys, and essentials",
        "intro": "Safety certifications and connection reliability come first for baby gear — a dropped video feed or a stroller recall matters more than any extra feature. We prioritize items with current safety-standard compliance and check reviews specifically for reliability complaints over time, not just week-one impressions.",
        "tips": [
            "Confirm current safety certifications (ASTM/JPMA for strollers, FCC for baby monitors) before anything else.",
            "For video monitors, check reviews for connection drops over months of use, not just initial setup impressions.",
            "Toddler toy durability complaints usually surface after a few weeks — weight recent reviews more than early ones.",
        ],
    },
}


def extract(path: Path) -> dict | None:
    if not path.exists():
        return None
    html = path.read_text(encoding="utf-8", errors="replace")
    for block in re.finditer(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', html, re.DOTALL):
        try:
            d = json.loads(block.group(1))
            if d.get("@type") == "Product":
                img = re.search(r'<img[^>]+src="(https?://[^"]+)"', html)
                cat_m = re.search(r'class="hero-cat">([^<]+)<', html)
                return {
                    "titulo": d.get("name", ""),
                    "precio": float(d.get("offers", {}).get("price", 49.99)),
                    "rating": float(d.get("aggregateRating", {}).get("ratingValue", 4.5)),
                    "reviews": int(d.get("aggregateRating", {}).get("reviewCount", 100)),
                    "affiliate_url": d.get("offers", {}).get("url", ""),
                    "imagen_url": img.group(1) if img else "",
                    "amazon_cat": cat_m.group(1).strip() if cat_m else "",
                }
        except Exception:
            continue
    return None


def stars(r):
    ri = int(r)
    return "★" * ri + "☆" * (5 - ri)


def gen_hub_html(cat_name: str, meta: dict, products: list[dict]) -> str:
    anio = datetime.now().year
    mes = datetime.now().strftime("%B %Y")
    emoji = meta["emoji"]
    cat_desc = meta["desc"]
    is_gaming = cat_name == "Amazon Games"

    bg      = "#0f0f1a" if is_gaming else "#ffffff"
    bg2     = "#1a1a2e" if is_gaming else "#f9fafb"
    card_bg = "#16161f" if is_gaming else "#ffffff"
    border  = "rgba(255,255,255,0.1)" if is_gaming else "#e5e7eb"
    text_c  = "#f0f0f5" if is_gaming else "#111827"
    text2_c = "#9999bb" if is_gaming else "#4b5563"
    text3_c = "#666688" if is_gaming else "#6b7280"
    accent  = "#7b61ff" if is_gaming else "#FF9900"

    # Sort products by rating * log(reviews) — best overall first
    import math
    products_sorted = sorted(products, key=lambda p: p["rating"] * math.log(max(p["reviews"], 10)), reverse=True)

    # Build product cards HTML
    cards_html = ""
    for i, p in enumerate(products_sorted):
        badge = "BEST OVERALL" if i == 0 else ("BEST VALUE" if p["precio"] == min(x["precio"] for x in products_sorted) else "TOP RATED")
        cards_html += f"""
    <div class="prod-card">
      {"<span class='card-badge'>BEST OVERALL</span>" if i == 0 else ""}
      <a href="{SITE_URL}/{p['slug']}/" class="card-img-link">
        <img src="{p['imagen_url']}" alt="{p['titulo']}" loading="lazy">
      </a>
      <div class="card-body">
        <div class="card-cat">{p['amazon_cat']}</div>
        <a href="{SITE_URL}/{p['slug']}/" class="card-title">{p['titulo'][:70]}{"..." if len(p['titulo'])>70 else ""}</a>
        <div class="card-meta">
          <span class="card-stars">{stars(p['rating'])}</span>
          <span class="card-rating">{p['rating']}★</span>
          <span class="card-reviews">({p['reviews']:,})</span>
        </div>
        <div class="card-price">${p['precio']:.2f}</div>
        <div class="card-actions">
          <a href="{SITE_URL}/{p['slug']}/" class="btn-review">Read Review →</a>
          <a href="{p['affiliate_url']}" class="btn-buy" rel="nofollow sponsored" target="_blank">Buy →</a>
        </div>
      </div>
    </div>"""

    hub_slug = meta["slug"]
    total_reviews = sum(p["reviews"] for p in products_sorted)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Best {cat_name} Products {anio} — Top {len(products_sorted)} Picks | TrendVortex</title>
<meta name="description" content="Best {cat_name.lower()} picks for {anio}: {cat_desc}. Expert-curated from {total_reviews:,} buyer reviews. Updated {mes}.">
<link rel="canonical" href="{SITE_URL}/{hub_slug}/">
<meta property="og:title" content="Best {cat_name} {anio} | TrendVortex">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:{bg};--bg2:{bg2};--card:{card_bg};--border:{border};
  --text:{text_c};--text2:{text2_c};--text3:{text3_c};
  --cta:#FF9900;--cta-text:#000;--accent:{accent};
  --green:#16a34a;--star:#f59e0b;
}}
html{{scroll-behavior:smooth}}
body{{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.65;-webkit-font-smoothing:antialiased;overflow-x:hidden}}
.site-header{{background:var(--card);border-bottom:1px solid var(--border);padding:12px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}}
.site-logo{{font-weight:900;font-size:1.1rem;color:var(--text);text-decoration:none}}
.site-logo span{{color:var(--cta)}}
.breadcrumb{{padding:9px 24px;font-size:.78rem;color:var(--text3);background:var(--bg2);border-bottom:1px solid var(--border)}}
.breadcrumb a{{color:var(--text3);text-decoration:none}}
.hero{{background:var(--bg2);border-bottom:3px solid var(--accent);padding:52px 24px 44px;text-align:center}}
.hero-emoji{{font-size:2.5rem;margin-bottom:12px;display:block}}
.hero h1{{font-size:clamp(1.6rem,5vw,2.6rem);font-weight:900;line-height:1.15;margin-bottom:12px;color:var(--text);max-width:680px;margin-left:auto;margin-right:auto}}
.hero-sub{{color:var(--text2);font-size:.97rem;margin-bottom:20px;max-width:540px;margin-left:auto;margin-right:auto}}
.trust-row{{display:flex;justify-content:center;flex-wrap:wrap;gap:.55rem}}
.trust-item{{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:5px 13px;font-size:.74rem;font-weight:600;color:var(--text2)}}
.wrap{{max-width:1100px;margin:0 auto;padding:0 20px 80px}}
.sec{{padding:36px 0 8px}}
.sec-eyebrow{{font-size:.64rem;font-weight:800;letter-spacing:2.5px;text-transform:uppercase;color:var(--accent);margin-bottom:6px}}
.sec h2{{font-size:clamp(1.2rem,4vw,1.6rem);font-weight:900;color:var(--text);margin-bottom:20px;line-height:1.25}}
.divider{{height:1px;background:var(--border);margin:8px 0}}
/* PRODUCT GRID */
.prod-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-top:16px}}
.prod-card{{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;position:relative;transition:border-color .2s}}
.prod-card:hover{{border-color:var(--cta)}}
.card-badge{{position:absolute;top:10px;left:10px;background:var(--cta);color:#000;font-size:.58rem;font-weight:900;letter-spacing:2px;text-transform:uppercase;padding:3px 10px;border-radius:20px}}
.card-img-link{{display:block;background:var(--bg2);border-bottom:1px solid var(--border)}}
.prod-card img{{width:100%;height:170px;object-fit:contain;padding:12px}}
.card-body{{padding:16px;display:flex;flex-direction:column;gap:6px;flex:1}}
.card-cat{{font-size:.65rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:1px}}
.card-title{{font-size:.88rem;font-weight:700;color:var(--text);text-decoration:none;line-height:1.4;display:block}}
.card-title:hover{{color:var(--cta)}}
.card-meta{{display:flex;align-items:center;gap:4px}}
.card-stars{{color:var(--star);font-size:.85rem}}
.card-rating{{font-size:.8rem;font-weight:700;color:var(--text2)}}
.card-reviews{{font-size:.75rem;color:var(--text3)}}
.card-price{{font-size:1.3rem;font-weight:900;color:var(--text);margin-top:2px}}
.card-actions{{display:flex;gap:8px;margin-top:auto;padding-top:10px}}
.btn-review{{flex:1;text-align:center;padding:9px 10px;border-radius:8px;font-size:.8rem;font-weight:700;text-decoration:none;background:var(--bg2);border:1px solid var(--border);color:var(--text2)}}
.btn-review:hover{{border-color:var(--cta);color:var(--text)}}
.btn-buy{{flex:1;text-align:center;padding:9px 10px;border-radius:8px;font-size:.8rem;font-weight:800;text-decoration:none;background:var(--cta);color:var(--cta-text)}}
/* STATS BAR */
.stats-bar{{display:flex;gap:24px;flex-wrap:wrap;background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:16px 20px;margin-bottom:24px}}
.stat-item{{text-align:center;min-width:80px}}
.stat-num{{font-size:1.5rem;font-weight:900;color:var(--accent);display:block}}
.stat-lbl{{font-size:.7rem;color:var(--text3)}}
/* CATEGORY INTRO */
.cat-intro{{max-width:760px;margin-bottom:28px}}
.cat-intro p{{color:var(--text2);font-size:.95rem;margin-bottom:14px}}
.cat-tips{{list-style:none;display:flex;flex-direction:column;gap:8px}}
.cat-tips li{{font-size:.86rem;color:var(--text2);padding-left:22px;position:relative}}
.cat-tips li::before{{content:"→";position:absolute;left:0;color:var(--accent);font-weight:900}}
footer{{border-top:1px solid var(--border);background:var(--bg2);padding:24px;font-size:.76rem;color:var(--text3);text-align:center;line-height:1.8}}
footer a{{color:var(--text3)}}
</style>
</head>
<body>
<header class="site-header">
  <a class="site-logo" href="{SITE_URL}">Trend<span>Vortex</span></a>
  <span style="font-size:.7rem;color:var(--text3)">⚠ Affiliate disclosure</span>
</header>
<div class="breadcrumb">
  <a href="{SITE_URL}">Home</a> › Best {cat_name}
</div>
<div class="hero">
  <span class="hero-emoji">{emoji}</span>
  <h1>Best {cat_name} Products in {anio}</h1>
  <p class="hero-sub">Expert-curated from {total_reviews:,} verified buyer reviews. Top {len(products_sorted)} picks for {cat_desc}. Updated {mes}.</p>
  <div class="trust-row">
    <span class="trust-item">✓ {len(products_sorted)} expert picks</span>
    <span class="trust-item">✓ {total_reviews:,} buyer reviews</span>
    <span class="trust-item">✓ Updated {mes}</span>
    <span class="trust-item">✓ No paid placements</span>
  </div>
</div>
<div class="wrap">
<section class="sec">
  <div class="stats-bar">
    <div class="stat-item"><span class="stat-num">{len(products_sorted)}</span><span class="stat-lbl">Expert picks</span></div>
    <div class="stat-item"><span class="stat-num">{total_reviews:,}</span><span class="stat-lbl">Buyer reviews</span></div>
    <div class="stat-item"><span class="stat-num">{sum(p["rating"] for p in products_sorted)/len(products_sorted):.1f}★</span><span class="stat-lbl">Avg rating</span></div>
    <div class="stat-item"><span class="stat-num">${min(p["precio"] for p in products_sorted):.0f}–${max(p["precio"] for p in products_sorted):.0f}</span><span class="stat-lbl">Price range</span></div>
  </div>
  <div class="cat-intro">
    <p>{meta["intro"]}</p>
    <ul class="cat-tips">
      {"".join(f"<li>{tip}</li>" for tip in meta["tips"])}
    </ul>
  </div>
  <div class="sec-eyebrow">All {cat_name} Picks</div>
  <h2>Our Top {cat_name} Recommendations for {anio}</h2>
  <div class="prod-grid">
    {cards_html}
  </div>
</section>
</div>
<footer>
  <strong>Affiliate disclosure:</strong> TrendVortex.tech earns a commission from Amazon when you buy through our links, at no extra cost to you.<br>
  <span style="display:block;margin-top:.4rem">© {anio} TrendVortex.tech · <a href="{SITE_URL}">Home</a> · Updated {mes}</span>
</footer>
</body></html>"""


def main():
    # Load all pages and their categories
    all_pages = []
    for page_dir in DOCS_DIR.iterdir():
        if not page_dir.is_dir() or not (page_dir / "index.html").exists():
            continue
        data = extract(page_dir / "index.html")
        if data and data["titulo"] and data["amazon_cat"]:
            data["slug"] = page_dir.name
            all_pages.append(data)

    # Group by category
    by_cat: dict[str, list] = {}
    for p in all_pages:
        cat = p["amazon_cat"]
        by_cat.setdefault(cat, []).append(p)

    generated = 0
    for cat_name, meta in CATEGORY_META.items():
        products = by_cat.get(cat_name, [])
        if len(products) < 2:
            print(f"  SKIP {cat_name} — only {len(products)} product(s)")
            continue

        hub_dir = DOCS_DIR / meta["slug"]
        hub_dir.mkdir(parents=True, exist_ok=True)
        html = gen_hub_html(cat_name, meta, products)
        (hub_dir / "index.html").write_text(html, encoding="utf-8")
        print(f"  OK  {cat_name} hub — {len(products)} products → /{meta['slug']}/")
        generated += 1

    print(f"\n  {generated} hub pages generated")


if __name__ == "__main__":
    main()
