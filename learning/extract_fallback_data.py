# -*- coding: utf-8 -*-
"""
learning/extract_fallback_data.py — Extrae los datos de producto ya
embebidos en cada pagina fallback (todas comparten la misma plantilla de
_fallback_html en agents/designer_agent.py), para poder regenerar el
copy sin depender de la API de Anthropic.

Uso:
  python learning/extract_fallback_data.py > learning/fallback_data.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "docs"
QUEUE_FILE = Path(__file__).parent / "regeneration_queue.json"


def extract_one(slug: str) -> dict | None:
    path = DOCS_DIR / f"best-{slug}" / "index.html"
    if not path.exists():
        return None
    html = path.read_text(encoding="utf-8", errors="ignore")

    def find(pattern, default=""):
        m = re.search(pattern, html, re.DOTALL)
        return m.group(1).strip() if m else default

    category = find(r'<div class="hero-cat">(.*?)</div>')
    title = find(r'class="prod-title"[^>]*>(.*?)</a>')
    price = find(r'<div class="prod-price">\$([\d.]+)</div>')
    rating = find(r'<span class="prod-rating-val">([\d.]+)★</span>')
    reviews = find(r'\(([\d,]+) verified reviews\)')
    affiliate_url = find(r'<a class="prod-title"[^>]*href="([^"]+)"')
    image_url = find(r'<img src="([^"]+)"[^>]*loading="eager"')
    keyword = slug.replace("-", " ")

    return {
        "slug": slug,
        "keyword": keyword,
        "category": category or "General",
        "product_title": title,
        "price": price,
        "rating": rating,
        "reviews": reviews.replace(",", ""),
        "affiliate_url": affiliate_url,
        "image_url": image_url,
    }


def main():
    if not QUEUE_FILE.exists():
        print("Corre primero: python learning/find_thin_pages.py --write-queue")
        return
    slugs = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))["pending_regeneration"]
    out = []
    for slug in slugs:
        data = extract_one(slug)
        if data:
            out.append(data)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
