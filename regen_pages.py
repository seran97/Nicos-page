# -*- coding: utf-8 -*-
"""
regen_pages.py — Regenerate all existing pages with the new light-theme design.
Reads product data from JSON-LD embedded in each existing page.
"""
import sys, os, re, json
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from dotenv import load_dotenv
load_dotenv()

from agents.designer_agent import DesignerAgent, slug

DOCS_DIR = Path("docs")

def extract_from_html(html_text: str) -> dict | None:
    """Extract product data from existing page JSON-LD + HTML."""
    # Product JSON-LD
    m = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', html_text, re.DOTALL)
    if not m:
        return None

    # Try each JSON-LD block for Product type
    product_data = None
    for block in re.finditer(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', html_text, re.DOTALL):
        try:
            data = json.loads(block.group(1))
            if data.get("@type") == "Product":
                product_data = data
                break
        except Exception:
            continue

    if not product_data:
        return None

    try:
        rating = float(product_data.get("aggregateRating", {}).get("ratingValue", 4.5))
        reviews = int(product_data.get("aggregateRating", {}).get("reviewCount", 100))
        precio = float(product_data.get("offers", {}).get("price", 49.99))
        affiliate_url = product_data.get("offers", {}).get("url", "https://amazon.com")
        titulo = product_data.get("name", "")
    except Exception:
        return None

    # Image URL from <img> tag in product card area
    img_match = re.search(r'<img[^>]+src="(https?://[^"]+)"[^>]*(?:loading|alt)=', html_text)
    imagen_url = img_match.group(1) if img_match else "https://via.placeholder.com/200"

    # Category from .hero-cat or .hero-badge div
    cat_match = re.search(r'class="hero-cat">([^<]+)<', html_text)
    if not cat_match:
        cat_match = re.search(r'class="hero-badge">([^·<]+)', html_text)
    amazon_cat = cat_match.group(1).strip() if cat_match else ""

    # Subreddit from "r/" reference
    sub_match = re.search(r'r/([a-zA-Z0-9_]+)', html_text)
    subreddit = sub_match.group(1) if sub_match else "deals"

    # Keyword from directory name (stripped later by caller)
    return {
        "titulo": titulo,
        "precio": precio,
        "rating": rating,
        "reviews": reviews,
        "imagen_url": imagen_url,
        "affiliate_url": affiliate_url,
        "source": "amazon",
        "amazon_cat": amazon_cat,
        "subreddit": subreddit,
    }


def main():
    designer = DesignerAgent()
    page_dirs = sorted([d for d in DOCS_DIR.iterdir() if d.is_dir() and (d / "index.html").exists()])
    print(f"Regenerando {len(page_dirs)} páginas con nuevo diseño light-theme...")

    ok = 0
    skip = 0
    for page_dir in page_dirs:
        index_file = page_dir / "index.html"
        html_text = index_file.read_text(encoding="utf-8", errors="replace")

        # Extract data
        data = extract_from_html(html_text)
        if not data or not data["titulo"]:
            print(f"  ⏭ SKIP {page_dir.name} — no product data found")
            skip += 1
            continue

        # Keyword from directory name: strip "best-" prefix
        dir_name = page_dir.name  # e.g. "best-air-fryer"
        keyword = dir_name.removeprefix("best-").replace("-", " ")

        amazon = {
            "titulo": data["titulo"],
            "precio": data["precio"],
            "rating": data["rating"],
            "reviews": data["reviews"],
            "imagen_url": data["imagen_url"],
            "affiliate_url": data["affiliate_url"],
            "source": data["source"],
        }
        trend = {}  # not needed for new design
        subreddit = data["subreddit"]
        amazon_cat = data["amazon_cat"] or "General"

        new_html = designer._fallback_html(keyword, amazon, trend, subreddit, amazon_cat)
        index_file.write_text(new_html, encoding="utf-8")
        print(f"  ✓ {page_dir.name} | {amazon_cat} | {amazon['rating']}★ ${amazon['precio']:.2f}")
        ok += 1

    print(f"\n{'='*50}")
    print(f"  ✅ Regeneradas: {ok} | ⏭ Saltadas: {skip}")
    print(f"  Listo — hacer git push para publicar")

if __name__ == "__main__":
    main()
