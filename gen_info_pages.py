# -*- coding: utf-8 -*-
"""gen_info_pages.py — Generate zero-affiliate-link informational guide pages
(the "50%" informational tier of the 50/20/20/10 content mix). Content is
hand-authored ahead of time into INFO_CONTENT_FILE (a JSON manifest), not
fetched live from an API — same pattern as gen_hub_pages.py's static
CATEGORY_META dict, to avoid the "ran out of API credit mid-run" failure
mode from a past regen incident.
"""
import sys, re, json, math
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
INFO_CONTENT_FILE = Path("info_content_manifest.json")

# slug -> (category display name, hub slug) — must match keys used by
# gen_hub_pages.py's CATEGORY_META / add_internal_links.py's CATEGORY_HUB.
TOPIC_CATEGORY = {
    "how-to-season-cast-iron-cookware":            ("Kitchen & Dining", "best-kitchen-dining"),
    "how-to-choose-air-fryer-size":                ("Kitchen & Dining", "best-kitchen-dining"),
    "sous-vide-times-temperatures-guide":           ("Kitchen & Dining", "best-kitchen-dining"),

    "mechanical-keyboard-switch-types-explained":   ("Amazon Games", "best-gaming-gear"),
    "how-to-reduce-wireless-mouse-input-lag":       ("Amazon Games", "best-gaming-gear"),
    "what-is-a-hot-swappable-keyboard":             ("Amazon Games", "best-gaming-gear"),

    "how-to-choose-dashcam-memory-card":            ("Automotive", "best-automotive"),
    "dashcam-resolution-night-vision-explained":    ("Automotive", "best-automotive"),
    "how-to-install-universal-seat-covers":         ("Automotive", "best-automotive"),

    "how-to-read-dog-food-ingredient-label":        ("Pet Supplies", "best-pet-supplies"),
    "grain-free-vs-grain-inclusive-dog-food":       ("Pet Supplies", "best-pet-supplies"),
    "how-to-introduce-pet-water-fountain":          ("Pet Supplies", "best-pet-supplies"),

    "how-to-find-true-running-shoe-size":           ("Sports & Outdoors", "best-sports-outdoors"),
    "camping-gear-weight-vs-durability-guide":       ("Sports & Outdoors", "best-sports-outdoors"),
    "yoga-mat-thickness-material-guide":            ("Sports & Outdoors", "best-sports-outdoors"),

    "gold-tone-vs-gold-filled-vs-gold-plated":      ("Fashion", "best-fashion"),
    "how-to-measure-wrist-for-watch-size":          ("Fashion", "best-fashion"),
    "how-to-care-for-leather-wallet":               ("Fashion", "best-fashion"),

    "cadr-rating-explained-air-purifier-sizing":    ("Home Improvement", "best-home-improvement"),
    "robot-vacuum-mapping-navigation-guide":        ("Home Improvement", "best-home-improvement"),
    "how-to-reduce-dehumidifier-running-costs":     ("Home Improvement", "best-home-improvement"),

    "how-to-patch-test-skincare-products":          ("Luxury Beauty", "best-beauty"),
    "vitamin-c-serum-concentration-guide":          ("Luxury Beauty", "best-beauty"),
    "mineral-vs-chemical-sunscreen-guide":          ("Luxury Beauty", "best-beauty"),

    "baby-monitor-safety-certifications-explained": ("Toys & Baby", "best-baby-products"),
    "how-to-childproof-home-room-by-room":          ("Toys & Baby", "best-baby-products"),
    "how-to-check-stroller-safety-recalls":         ("Toys & Baby", "best-baby-products"),
}


def extract_product(path: Path) -> dict | None:
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
                    "rating": float(d.get("aggregateRating", {}).get("ratingValue", 4.5)),
                    "reviews": int(d.get("aggregateRating", {}).get("reviewCount", 100)),
                    "imagen_url": img.group(1) if img else "",
                    "amazon_cat": cat_m.group(1).strip() if cat_m else "",
                }
        except Exception:
            continue
    return None


def top_reviews_for_category(cat_name: str, n: int = 3) -> list[dict]:
    scored = []
    for page_dir in DOCS_DIR.iterdir():
        if not page_dir.is_dir() or not (page_dir / "index.html").exists():
            continue
        if page_dir.name in TOPIC_CATEGORY or "-vs-" in page_dir.name:
            continue
        data = extract_product(page_dir / "index.html")
        if data and data["amazon_cat"] == cat_name and data["titulo"]:
            data["slug"] = page_dir.name
            scored.append(data)
    scored.sort(key=lambda x: x["rating"] * math.log(max(x["reviews"], 10)), reverse=True)
    return scored[:n]


def render_guide_html(slug: str, content: dict, cat_name: str, hub_slug: str, related: list[dict]) -> str:
    anio = datetime.now().year
    mes = datetime.now().strftime("%B %Y")
    title = content["title"]
    meta_desc = content["meta_description"]
    intro = content["intro"]
    sections = content["sections"]
    faq = content["faq"]

    sections_html = "".join(
        f'<section class="g-sec"><h2>{s["heading"]}</h2>'
        + "".join(f"<p>{para}</p>" for para in s["body"].split("\n\n") if para.strip())
        + "</section>"
        for s in sections
    )

    faq_html = "".join(
        f'<div class="faq-item"><div class="faq-q">{f["q"]}</div><div class="faq-a">{f["a"]}</div></div>'
        for f in faq
    )

    faq_jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in faq
        ],
    }
    article_jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "author": {"@type": "Organization", "name": "TrendVortex"},
        "publisher": {"@type": "Organization", "name": "TrendVortex"},
        "datePublished": datetime.now().strftime("%Y-%m-%d"),
    }

    related_cards = "".join(
        f'''<a href="{SITE_URL}/{p['slug']}/" class="rel-card">
    <img src="{p['imagen_url']}" alt="{p['titulo']}" loading="lazy">
    <div class="rel-body">
      <div class="rel-title">{p['titulo'][:55]}{"..." if len(p['titulo']) > 55 else ""}</div>
      <div class="rel-meta">{p['rating']}★ ({p['reviews']:,} reviews)</div>
    </div>
  </a>'''
        for p in related
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>{title} | TrendVortex</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{SITE_URL}/{slug}/">
<meta property="og:title" content="{title} | TrendVortex">
<meta property="og:description" content="{meta_desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<script type="application/ld+json">
{json.dumps(article_jsonld, ensure_ascii=False)}
</script>
<script type="application/ld+json">
{json.dumps(faq_jsonld, ensure_ascii=False)}
</script>
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#ffffff;--bg2:#f9fafb;--card:#ffffff;--border:#e5e7eb;
  --text:#111827;--text2:#4b5563;--text3:#6b7280;
  --accent:#0ea5e9;
}}
body{{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.7;-webkit-font-smoothing:antialiased}}
.site-header{{background:var(--card);border-bottom:1px solid var(--border);padding:12px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}}
.site-logo{{font-weight:900;font-size:1.1rem;color:var(--text);text-decoration:none}}
.site-logo span{{color:#FF9900}}
.badge-guide{{font-size:.68rem;font-weight:700;color:var(--accent);background:#e0f2fe;border-radius:20px;padding:4px 12px}}
.breadcrumb{{padding:9px 24px;font-size:.78rem;color:var(--text3);background:var(--bg2);border-bottom:1px solid var(--border)}}
.breadcrumb a{{color:var(--text3);text-decoration:none}}
.wrap{{max-width:720px;margin:0 auto;padding:40px 20px 60px}}
h1{{font-size:clamp(1.5rem,4vw,2.1rem);font-weight:900;line-height:1.2;margin-bottom:10px}}
.lead{{color:var(--text2);font-size:1rem;margin-bottom:28px}}
.g-sec{{margin-bottom:24px}}
.g-sec h2{{font-size:1.15rem;font-weight:800;margin-bottom:10px;color:var(--text)}}
.g-sec p{{color:var(--text2);font-size:.95rem;margin-bottom:12px}}
.faq-item{{border-top:1px solid var(--border);padding:16px 0}}
.faq-q{{font-weight:700;font-size:.95rem;margin-bottom:6px}}
.faq-a{{color:var(--text2);font-size:.9rem}}
.related-h{{font-size:1.05rem;font-weight:900;margin:32px 0 14px}}
.related-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px}}
.rel-card{{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;text-decoration:none;display:flex;flex-direction:column}}
.rel-card:hover{{border-color:#FF9900}}
.rel-card img{{width:100%;height:90px;object-fit:contain;background:var(--bg2);padding:8px;border-bottom:1px solid var(--border)}}
.rel-body{{padding:10px}}
.rel-title{{font-size:.76rem;font-weight:600;color:var(--text);line-height:1.4;margin-bottom:4px}}
.rel-meta{{font-size:.7rem;color:var(--text3)}}
.hub-link{{display:inline-block;margin-bottom:20px;font-size:.85rem;font-weight:700;color:#FF9900;text-decoration:none}}
footer{{border-top:1px solid var(--border);background:var(--bg2);padding:24px;font-size:.76rem;color:var(--text3);text-align:center;line-height:1.8}}
footer a{{color:var(--text3)}}
</style>
</head>
<body>
<header class="site-header">
  <a class="site-logo" href="{SITE_URL}">Trend<span>Vortex</span></a>
  <span class="badge-guide">📘 Free guide — no product links</span>
</header>
<div class="breadcrumb">
  <a href="{SITE_URL}">Home</a> › <a href="{SITE_URL}/{hub_slug}/">{cat_name}</a> › Guide
</div>
<div class="wrap">
  <h1>{title}</h1>
  <p class="lead">{intro}</p>
  {sections_html}
  <h2 style="font-size:1.15rem;font-weight:800;margin:32px 0 10px">FAQ</h2>
  {faq_html}
  <a class="hub-link" href="{SITE_URL}/{hub_slug}/">← Back to Best {cat_name}</a>
  <div class="related-h">Related Reviews</div>
  <div class="related-grid">{related_cards}</div>
</div>
<footer>
  This is an independent, ad-free educational guide — no product links or commissions on this page.<br>
  <span style="display:block;margin-top:.4rem">© {anio} TrendVortex.tech · <a href="{SITE_URL}">Home</a> ·
  <a href="/privacy-policy.html">Privacy Policy</a> · <a href="/legal-notice.html">Legal Notice</a> ·
  <a href="/terms-of-use.html">Terms of Use</a> · Updated {mes}</span>
</footer>
</body></html>"""


def main():
    if not INFO_CONTENT_FILE.exists():
        print(f"  ERROR: {INFO_CONTENT_FILE} not found — nothing to generate")
        return
    all_content = json.loads(INFO_CONTENT_FILE.read_text(encoding="utf-8"))

    generated = 0
    for content in all_content:
        slug = content["slug"]
        if slug not in TOPIC_CATEGORY:
            print(f"  SKIP {slug} — not in TOPIC_CATEGORY mapping")
            continue
        cat_name, hub_slug = TOPIC_CATEGORY[slug]
        related = top_reviews_for_category(cat_name, 3)

        page_dir = DOCS_DIR / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        html = render_guide_html(slug, content, cat_name, hub_slug, related)
        (page_dir / "index.html").write_text(html, encoding="utf-8")
        print(f"  OK  {slug} → /{slug}/  ({len(related)} related reviews linked)")
        generated += 1

    print(f"\n  {generated} informational guide pages generated")


if __name__ == "__main__":
    main()
