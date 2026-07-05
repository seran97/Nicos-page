# -*- coding: utf-8 -*-
"""add_internal_links.py — Inject "Related Reviews" section into all product pages."""
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

CATEGORY_HUB = {
    "Kitchen & Dining":  "best-kitchen-dining",
    "Amazon Games":      "best-gaming-gear",
    "Automotive":        "best-automotive",
    "Pet Supplies":      "best-pet-supplies",
    "Sports & Outdoors": "best-sports-outdoors",
    "Fashion":           "best-fashion",
    "Home Improvement":  "best-home-improvement",
    "Luxury Beauty":     "best-beauty",
    "Toys & Baby":       "best-baby-products",
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
                    "imagen_url": img.group(1) if img else "",
                    "amazon_cat": cat_m.group(1).strip() if cat_m else "",
                }
        except Exception:
            continue
    return None


def stars(r):
    ri = int(r)
    return "★" * ri + "☆" * (5 - ri)


def build_related_html(current_slug: str, related: list[dict], cat_name: str) -> str:
    hub_slug = CATEGORY_HUB.get(cat_name, "")
    hub_link = f'<a href="{SITE_URL}/{hub_slug}/" style="color:var(--cta);font-size:.82rem;font-weight:700;text-decoration:none">View all {cat_name} →</a>' if hub_slug else ""
    cards = ""
    for p in related[:4]:
        cards += f"""
  <a href="{SITE_URL}/{p['slug']}/" class="rel-card">
    <img src="{p['imagen_url']}" alt="{p['titulo']}" loading="lazy">
    <div class="rel-body">
      <div class="rel-title">{p['titulo'][:55]}{"..." if len(p['titulo'])>55 else ""}</div>
      <div class="rel-meta"><span style="color:#f59e0b">{stars(p['rating'])}</span> {p['rating']}★</div>
      <div class="rel-price">${p['precio']:.2f}</div>
    </div>
  </a>"""

    return f"""
<style>
.related-wrap{{max-width:820px;margin:0 auto;padding:0 20px 24px}}
.related-h{{font-size:1.05rem;font-weight:900;color:var(--text);margin-bottom:14px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}}
.related-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}}
.rel-card{{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;text-decoration:none;display:flex;flex-direction:column;transition:border-color .2s}}
.rel-card:hover{{border-color:var(--cta)}}
.rel-card img{{width:100%;height:100px;object-fit:contain;background:var(--bg2);padding:8px;border-bottom:1px solid var(--border)}}
.rel-body{{padding:10px}}
.rel-title{{font-size:.78rem;font-weight:600;color:var(--text);line-height:1.4;margin-bottom:5px}}
.rel-meta{{font-size:.72rem;color:var(--text2)}}
.rel-price{{font-size:.95rem;font-weight:900;color:var(--text);margin-top:4px}}
</style>
<div class="related-wrap">
  <div class="related-h">
    <span>More {cat_name} Reviews</span>
    {hub_link}
  </div>
  <div class="related-grid">{cards}
  </div>
</div>"""


def main():
    # Load all product pages
    all_pages = []
    for page_dir in DOCS_DIR.iterdir():
        if not page_dir.is_dir() or not (page_dir / "index.html").exists():
            continue
        # Skip hub, vs, and non-product pages
        name = page_dir.name
        if "-vs-" in name or name in [
            "best-kitchen-dining", "best-gaming-gear", "best-automotive",
            "best-pet-supplies", "best-sports-outdoors", "best-fashion",
            "best-home-improvement", "best-beauty", "best-baby-products"
        ]:
            continue
        data = extract(page_dir / "index.html")
        if data and data["titulo"] and data["amazon_cat"]:
            data["slug"] = name
            all_pages.append(data)

    # Group by category
    by_cat: dict[str, list] = {}
    for p in all_pages:
        cat = p["amazon_cat"]
        by_cat.setdefault(cat, []).append(p)

    updated = 0
    for p in all_pages:
        cat = p["amazon_cat"]
        same_cat = [x for x in by_cat.get(cat, []) if x["slug"] != p["slug"]]
        if not same_cat:
            continue

        # Pick top 4 by rating × log(reviews)
        related = sorted(same_cat, key=lambda x: x["rating"] * math.log(max(x["reviews"], 10)), reverse=True)[:4]

        page_file = DOCS_DIR / p["slug"] / "index.html"
        html = page_file.read_text(encoding="utf-8", errors="replace")

        # Skip if already has related section
        if "related-wrap" in html:
            continue

        # Inject before </body>
        injection = build_related_html(p["slug"], related, cat)
        new_html = html.replace("</body>", f"{injection}\n</body>")

        if new_html != html:
            page_file.write_text(new_html, encoding="utf-8")
            updated += 1
            print(f"  OK  {p['slug']} — {len(related)} related links added")

    print(f"\n  {updated} pages updated with internal links")


if __name__ == "__main__":
    main()
