# -*- coding: utf-8 -*-
"""gen_vs_pages.py — Generate "X vs Y" comparison pages (highest conversion: 8-15%)"""
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

# ── VS pairs to generate ────────────────────────────────────────────────────────
VS_PAIRS = [
    # Kitchen
    ("best-cuisinart-air-fryer",           "best-breville-smart-oven-air-fryer-pro"),
    ("best-air-fryer",                     "best-cuisinart-air-fryer"),
    ("best-sous-vide",                     "best-sous-vide-cooker"),
    ("best-breville-smart-oven-air-fryer", "best-instant-pot-vortex-plus-10-quart-air-fryer-oven"),
    # Gaming
    ("best-drop-entr-mechanical-keyboard", "best-hyperx-alloy-origins-mechanical-gaming-keyboard"),
    ("best-hyperx-alloy-origins-mechanical-gaming-keyboard", "best-keychron-k10-wireless-mechanical-keyboard"),
    ("best-gaming-headset",                "best-gaming-mouse"),
    # Automotive
    ("best-dashcam",                       "best-wireless-dashcam"),
    ("best-dashcam-for-car",               "best-motorcycle-dashcam"),
    # Pet
    ("best-best-dog-food",                 "best-best-dog-food-with-grain"),
    ("best-best-dog-food",                 "best-purina-dog-food"),
    # Sports
    ("best-running-shoes",                 "best-adidas-running-shoes"),
    ("best-running-shoes",                 "best-nike-men-s-air-max-torch-4-running-shoes"),
]


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
                sub_m = re.search(r'r/([a-zA-Z0-9_]+)', html)
                return {
                    "titulo": d.get("name", ""),
                    "precio": float(d.get("offers", {}).get("price", 49.99)),
                    "rating": float(d.get("aggregateRating", {}).get("ratingValue", 4.5)),
                    "reviews": int(d.get("aggregateRating", {}).get("reviewCount", 100)),
                    "affiliate_url": d.get("offers", {}).get("url", ""),
                    "imagen_url": img.group(1) if img else "",
                    "amazon_cat": cat_m.group(1).strip() if cat_m else "General",
                    "subreddit": sub_m.group(1) if sub_m else "deals",
                }
        except Exception:
            continue
    return None


def stars(r):
    ri = int(r)
    return "★" * ri + "☆" * (5 - ri)


def gen_vs_html(a: dict, b: dict, slug_a: str, slug_b: str) -> str:
    anio = datetime.now().year
    mes = datetime.now().strftime("%B %Y")
    kw_a = slug_a.removeprefix("best-").replace("-", " ").title()
    kw_b = slug_b.removeprefix("best-").replace("-", " ").title()
    cat = a["amazon_cat"]
    is_gaming = cat == "Amazon Games"

    bg      = "#0f0f1a" if is_gaming else "#ffffff"
    bg2     = "#1a1a2e" if is_gaming else "#f9fafb"
    card_bg = "#16161f" if is_gaming else "#ffffff"
    border  = "rgba(255,255,255,0.1)" if is_gaming else "#e5e7eb"
    text_c  = "#f0f0f5" if is_gaming else "#111827"
    text2_c = "#9999bb" if is_gaming else "#4b5563"
    text3_c = "#666688" if is_gaming else "#6b7280"
    accent  = "#7b61ff" if is_gaming else "#FF9900"

    # Determine winner by composite score: rating*0.4 + reviews/5000*0.3 + (1/price)*30*0.3
    def score(p):
        return p["rating"] * 40 + min(p["reviews"] / 100, 30) + (30 / max(p["precio"], 10))
    winner = "a" if score(a) >= score(b) else "b"
    winner_label = kw_a if winner == "a" else kw_b
    winner_reason = (
        f"higher rating ({a['rating']}★ vs {b['rating']}★)" if a["rating"] > b["rating"]
        else f"more verified reviews ({a['reviews']:,} vs {b['reviews']:,})" if a["reviews"] > b["reviews"]
        else f"better price (${a['precio']:.2f} vs ${b['precio']:.2f})"
    )

    vs_slug = f"{slug_a}-vs-{slug_b}"
    a_title_s = a["titulo"].replace('"', "'")
    b_title_s = b["titulo"].replace('"', "'")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>{kw_a} vs {kw_b} ({anio}): Which One to Buy? | TrendVortex</title>
<meta name="description" content="{kw_a} vs {kw_b}: side-by-side comparison of price, rating, and features. Expert verdict based on {a['reviews']+b['reviews']:,} total buyer reviews. Updated {mes}.">
<link rel="canonical" href="{SITE_URL}/{vs_slug}/">
<meta property="og:title" content="{kw_a} vs {kw_b} ({anio}) | TrendVortex">
<meta property="og:description" content="Expert comparison: {a['rating']}★ {a['titulo'][:40]} vs {b['rating']}★ {b['titulo'][:40]}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{{"@type":"Question","name":"Which is better: {kw_a} or {kw_b}?","acceptedAnswer":{{"@type":"Answer","text":"Based on {a['reviews']+b['reviews']:,} combined buyer reviews, the {winner_label} wins due to {winner_reason}."}}}}]}}
</script>
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
.hero{{background:var(--bg2);border-bottom:3px solid var(--accent);padding:48px 24px 40px;text-align:center}}
.hero-cat{{display:inline-block;background:rgba(255,153,0,0.12);color:var(--cta);border:1px solid rgba(255,153,0,0.3);font-size:.68rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;padding:4px 14px;border-radius:20px;margin-bottom:14px}}
.hero h1{{font-size:clamp(1.5rem,4.5vw,2.4rem);font-weight:900;line-height:1.15;margin-bottom:12px;color:var(--text);max-width:740px;margin-left:auto;margin-right:auto}}
.hero-sub{{color:var(--text2);font-size:.95rem;margin-bottom:0;max-width:540px;margin-left:auto;margin-right:auto}}
.verdict-box{{background:rgba(22,163,74,0.06);border:1px solid rgba(22,163,74,.3);border-left:4px solid var(--green);padding:16px 20px;font-size:.9rem;color:var(--text2);line-height:1.6}}
.verdict-box strong{{color:var(--green);display:block;margin-bottom:4px;font-size:.72rem;text-transform:uppercase;letter-spacing:1.5px}}
.wrap{{max-width:860px;margin:0 auto;padding:0 20px 80px}}
.sec{{padding:36px 0 8px}}
.sec-eyebrow{{font-size:.64rem;font-weight:800;letter-spacing:2.5px;text-transform:uppercase;color:var(--accent);margin-bottom:6px}}
.sec h2{{font-size:clamp(1.2rem,4vw,1.55rem);font-weight:900;color:var(--text);margin-bottom:14px;line-height:1.25}}
.divider{{height:1px;background:var(--border);margin:6px 0}}
/* SIDE BY SIDE */
.vs-grid{{display:grid;grid-template-columns:1fr auto 1fr;gap:0;margin:16px 0;align-items:stretch}}
.vs-card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:10px}}
.vs-card.winner{{border-top:4px solid var(--cta);}}
.vs-badge{{display:inline-block;font-size:.6rem;font-weight:900;letter-spacing:2px;text-transform:uppercase;padding:3px 10px;border-radius:20px;margin-bottom:6px}}
.vs-badge.win{{background:var(--cta);color:#000}}
.vs-badge.runner{{background:var(--bg2);border:1px solid var(--border);color:var(--text3)}}
.vs-card img{{width:100%;max-height:150px;object-fit:contain;border-radius:8px;background:var(--bg2);border:1px solid var(--border);cursor:pointer;transition:opacity .15s}}
.vs-card img:hover{{opacity:.85}}
.vs-title{{font-size:.88rem;font-weight:700;color:var(--text);line-height:1.4}}
.vs-title:hover{{color:var(--cta)}}
.vs-price{{font-size:1.5rem;font-weight:900;color:var(--text)}}
.vs-stars{{color:var(--star);font-size:.95rem}}
.vs-reviews{{font-size:.75rem;color:var(--text3)}}
.vs-btn{{display:block;background:var(--cta);color:var(--cta-text);font-weight:800;font-size:.88rem;padding:12px 16px;border-radius:10px;text-decoration:none;text-align:center;margin-top:auto}}
.vs-sep{{display:flex;align-items:center;justify-content:center;padding:0 12px;font-size:1.1rem;font-weight:900;color:var(--text3)}}
@media(max-width:560px){{.vs-grid{{grid-template-columns:1fr;gap:12px}}.vs-sep{{display:none}}}}
/* COMPARISON TABLE */
.tabla-wrap{{overflow-x:auto;margin:14px 0;border-radius:12px;border:1px solid var(--border);-webkit-overflow-scrolling:touch}}
table{{width:100%;border-collapse:collapse;min-width:300px;font-size:.85rem}}
thead th{{background:var(--bg2);padding:10px 16px;text-align:left;font-size:.7rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border)}}
thead th.col-a{{color:var(--cta);background:rgba(255,153,0,.06)}}
thead th.col-b{{color:var(--accent)}}
tbody td{{padding:10px 16px;color:var(--text2);border-top:1px solid var(--border)}}
tbody td:first-child{{font-weight:600;color:var(--text)}}
.td-win{{color:var(--green);font-weight:700}}
.td-ok{{color:var(--text2)}}
tbody tr:hover td{{background:var(--bg2)}}
/* USE CASE */
.use-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0}}
@media(max-width:480px){{.use-grid{{grid-template-columns:1fr}}}}
.use-box{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px}}
.use-box h3{{font-size:.82rem;font-weight:800;margin-bottom:10px;color:var(--accent)}}
.use-box li{{font-size:.84rem;color:var(--text2);padding:4px 0 4px 18px;position:relative;list-style:none;line-height:1.5}}
.use-box li::before{{content:'→';position:absolute;left:0;color:var(--cta)}}
/* FAQ */
.faq-item{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:10px}}
.faq-item:hover{{border-color:var(--cta)}}
.faq-q{{font-weight:700;color:var(--text);margin-bottom:5px;font-size:.88rem}}
.faq-a{{font-size:.84rem;color:var(--text2);line-height:1.6}}
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
  <a href="{SITE_URL}">Home</a> › <a href="{SITE_URL}/{slug_a}/">{kw_a}</a> › vs {kw_b}
</div>
<div class="hero">
  <div class="hero-cat">{cat} Comparison</div>
  <h1>{kw_a} vs {kw_b} ({anio}): Which One Should You Buy?</h1>
  <p class="hero-sub">Side-by-side comparison based on {a['reviews']+b['reviews']:,} combined buyer reviews. Updated {mes}.</p>
</div>
<div class="verdict-box">
  <strong>⚡ Quick Verdict</strong>
  After comparing {a['reviews']+b['reviews']:,} reviews: <strong>{winner_label}</strong> wins thanks to {winner_reason}. Scroll down for the full breakdown.
</div>
<div class="wrap">
<section class="sec">
  <div class="sec-eyebrow">Head to Head</div>
  <h2>{kw_a} vs {kw_b} at a Glance</h2>
  <div class="vs-grid">
    <div class="vs-card{"  winner" if winner=="a" else ""}">
      <span class="vs-badge {"win" if winner=="a" else "runner"}">{"OUR PICK" if winner=="a" else "RUNNER-UP"}</span>
      <a href="{a['affiliate_url']}" rel="nofollow sponsored" target="_blank"><img src="{a['imagen_url']}" alt="{a['titulo']}" loading="eager"></a>
      <a class="vs-title" href="{a['affiliate_url']}" rel="nofollow sponsored" target="_blank" style="color:inherit;text-decoration:none">{a['titulo']}</a>
      <div class="vs-price">${a['precio']:.2f}</div>
      <div><span class="vs-stars">{stars(a['rating'])}</span> <span class="vs-reviews">{a['rating']}★ ({a['reviews']:,} reviews)</span></div>
      <a class="vs-btn" href="{a['affiliate_url']}" rel="nofollow sponsored" target="_blank">Check Price →</a>
    </div>
    <div class="vs-sep">VS</div>
    <div class="vs-card{"  winner" if winner=="b" else ""}">
      <span class="vs-badge {"win" if winner=="b" else "runner"}">{"OUR PICK" if winner=="b" else "RUNNER-UP"}</span>
      <a href="{b['affiliate_url']}" rel="nofollow sponsored" target="_blank"><img src="{b['imagen_url']}" alt="{b['titulo']}" loading="eager"></a>
      <a class="vs-title" href="{b['affiliate_url']}" rel="nofollow sponsored" target="_blank" style="color:inherit;text-decoration:none">{b['titulo']}</a>
      <div class="vs-price">${b['precio']:.2f}</div>
      <div><span class="vs-stars">{stars(b['rating'])}</span> <span class="vs-reviews">{b['rating']}★ ({b['reviews']:,} reviews)</span></div>
      <a class="vs-btn" href="{b['affiliate_url']}" rel="nofollow sponsored" target="_blank">Check Price →</a>
    </div>
  </div>
</section>
<div class="divider"></div>
<section class="sec">
  <div class="sec-eyebrow">Detailed Comparison</div>
  <h2>How They Compare: Key Metrics</h2>
  <div class="tabla-wrap">
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th class="col-a">{kw_a[:28]}</th>
          <th class="col-b">{kw_b[:28]}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Price</td>
          <td class="{"td-win" if a["precio"] <= b["precio"] else "td-ok"}">${a['precio']:.2f} {"✓" if a["precio"] <= b["precio"] else ""}</td>
          <td class="{"td-win" if b["precio"] <= a["precio"] else "td-ok"}">${b['precio']:.2f} {"✓" if b["precio"] <= a["precio"] else ""}</td>
        </tr>
        <tr>
          <td>Star Rating</td>
          <td class="{"td-win" if a["rating"] >= b["rating"] else "td-ok"}">{a['rating']}★ {"✓" if a["rating"] >= b["rating"] else ""}</td>
          <td class="{"td-win" if b["rating"] >= a["rating"] else "td-ok"}">{b['rating']}★ {"✓" if b["rating"] >= a["rating"] else ""}</td>
        </tr>
        <tr>
          <td>Verified Reviews</td>
          <td class="{"td-win" if a["reviews"] >= b["reviews"] else "td-ok"}">{a['reviews']:,} {"✓" if a["reviews"] >= b["reviews"] else ""}</td>
          <td class="{"td-win" if b["reviews"] >= a["reviews"] else "td-ok"}">{b['reviews']:,} {"✓" if b["reviews"] >= a["reviews"] else ""}</td>
        </tr>
        <tr>
          <td>Value Score</td>
          <td class="{"td-win" if score(a) >= score(b) else "td-ok"}">{score(a):.0f}/100 {"✓" if score(a) >= score(b) else ""}</td>
          <td class="{"td-win" if score(b) >= score(a) else "td-ok"}">{score(b):.0f}/100 {"✓" if score(b) >= score(a) else ""}</td>
        </tr>
      </tbody>
    </table>
  </div>
</section>
<div class="divider"></div>
<section class="sec">
  <div class="sec-eyebrow">Which One to Choose?</div>
  <h2>Buy by Use Case</h2>
  <div class="use-grid">
    <div class="use-box">
      <h3>✅ Buy {kw_a[:32]} if...</h3>
      <ul>
        <li>You prioritize {"lower price" if a["precio"] < b["precio"] else "higher ratings"}</li>
        <li>You want {a['reviews']:,} real buyer reviews to back the purchase</li>
        <li>{"Budget is a concern" if a["precio"] < b["precio"] else "Quality is non-negotiable"}</li>
      </ul>
    </div>
    <div class="use-box">
      <h3>✅ Buy {kw_b[:32]} if...</h3>
      <ul>
        <li>You prioritize {"lower price" if b["precio"] < a["precio"] else "higher ratings"}</li>
        <li>You want {b['reviews']:,} verified reviews backing the pick</li>
        <li>{"Budget is a concern" if b["precio"] < a["precio"] else "Quality is non-negotiable"}</li>
      </ul>
    </div>
  </div>
</section>
<div class="divider"></div>
<section class="sec">
  <div class="sec-eyebrow">FAQ</div>
  <h2>Common Questions</h2>
  <div class="faq-item">
    <div class="faq-q">Is {kw_a} better than {kw_b}?</div>
    <div class="faq-a">{"Yes — " if winner=="a" else "Not necessarily. "}{kw_a} {"wins" if winner=="a" else "trails"} on {winner_reason} based on {a['reviews']+b['reviews']:,} combined buyer reviews.</div>
  </div>
  <div class="faq-item">
    <div class="faq-q">What is the price difference between {kw_a} and {kw_b}?</div>
    <div class="faq-a">{kw_a} costs ${a['precio']:.2f} and {kw_b} costs ${b['precio']:.2f} — a difference of ${abs(a['precio']-b['precio']):.2f}. {"The cheaper option has fewer reviews." if min(a["precio"],b["precio"]) == a["precio"] and a["reviews"] < b["reviews"] else "Both offer strong value at their respective price points."}</div>
  </div>
  <div class="faq-item">
    <div class="faq-q">Which has better reviews: {kw_a} or {kw_b}?</div>
    <div class="faq-a">{"Both have strong ratings. " if abs(a["rating"]-b["rating"]) < 0.2 else ""}{kw_a} has {a['rating']}★ from {a['reviews']:,} reviews. {kw_b} has {b['rating']}★ from {b['reviews']:,} reviews. {"Higher volume generally means a more reliable average." if max(a["reviews"],b["reviews"]) > 1000 else ""}</div>
  </div>
  <div class="faq-item">
    <div class="faq-q">What is the overall winner: {kw_a} vs {kw_b}?</div>
    <div class="faq-a">Our overall pick is <strong>{winner_label}</strong> — it wins due to {winner_reason}. See the full comparison table above for a metric-by-metric breakdown.</div>
  </div>
</section>
<div style="background:rgba(255,153,0,.06);border:1px solid rgba(255,153,0,.25);border-radius:14px;padding:24px;margin:28px 0;text-align:center">
  <div style="font-weight:900;font-size:1.1rem;color:var(--text);margin-bottom:6px">Our Overall Recommendation</div>
  <div style="font-size:.88rem;color:var(--text2);margin-bottom:16px">{winner_label} — {winner_reason}. {a['reviews']+b['reviews']:,} combined buyer reviews support this call.</div>
  <a style="display:inline-block;background:#FF9900;color:#000;font-weight:800;font-size:1rem;padding:16px 36px;border-radius:10px;text-decoration:none" href="{a['affiliate_url'] if winner=='a' else b['affiliate_url']}" rel="nofollow sponsored" target="_blank">Check Best Price →</a>
</div>
</div>
<footer>
  <strong>Affiliate disclosure:</strong> TrendVortex.tech earns a commission from Amazon when you buy through our links, at no extra cost to you.<br>
  <span style="display:block;margin-top:.4rem">© {anio} TrendVortex.tech · <a href="{SITE_URL}">Home</a> · Updated {mes}</span>
</footer>
</body></html>"""


def main():
    generated = 0
    for slug_a, slug_b in VS_PAIRS:
        a = extract(DOCS_DIR / slug_a / "index.html")
        b = extract(DOCS_DIR / slug_b / "index.html")
        if not a or not b:
            print(f"  SKIP {slug_a} vs {slug_b} — missing page data")
            continue

        vs_slug = f"{slug_a}-vs-{slug_b}"
        out_dir = DOCS_DIR / vs_slug
        out_dir.mkdir(parents=True, exist_ok=True)

        html = gen_vs_html(a, b, slug_a, slug_b)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        kw_a = slug_a.removeprefix("best-").replace("-", " ").title()
        kw_b = slug_b.removeprefix("best-").replace("-", " ").title()
        print(f"  OK  {kw_a} vs {kw_b}")
        generated += 1

    print(f"\n  {generated} vs pages generated")


if __name__ == "__main__":
    main()
