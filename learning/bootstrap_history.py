# -*- coding: utf-8 -*-
"""
learning/bootstrap_history.py — Corre UNA SOLA VEZ para poblar
learning/history.jsonl con todo lo que TrendVortex ya generó antes de que
existiera el NicheLearner (las 282 páginas en docs/).

Sin esto, el learner "olvidaría" todo el trabajo previo y empezaría a
aprender desde cero. Cruza:
  - docs/best-*/index.html   → qué páginas existen, si son fallback
    (detecta la frase única de _fallback_html en designer_agent.py) y si
    son de eBay (sufijo "-ebay" en el slug).
  - leads.csv                → keyword → amazon_cat / comision_pct,
    para saber la categoría real de cada página ya publicada.

Uso:
  python learning/bootstrap_history.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from niche_learner import NicheLearner, HISTORY_FILE

DOCS_DIR = Path(__file__).parent.parent / "docs"
LEADS_CSV = Path(__file__).parent.parent / "leads.csv"

FALLBACK_MARKER = "look for these three factors before committing to any"


def _slug_to_keyword(slug: str) -> str:
    return slug.replace("-ebay", "").replace("-", " ").strip()


def main():
    if HISTORY_FILE.exists():
        print(f"⚠ {HISTORY_FILE} ya existe con datos — bórralo primero si "
              f"quieres re-generar el bootstrap desde cero.")
        return

    cat_by_keyword: dict[str, str] = {}
    if LEADS_CSV.exists():
        df = pd.read_csv(LEADS_CSV)
        for _, row in df.iterrows():
            kw = str(row.get("keyword", "")).strip().lower()
            if kw:
                cat_by_keyword[kw] = str(row.get("amazon_cat", "General"))

    learner = NicheLearner()
    count = 0
    for page_dir in sorted(DOCS_DIR.glob("best-*")):
        index_html = page_dir / "index.html"
        if not index_html.exists():
            continue

        slug = page_dir.name.removeprefix("best-")
        keyword = _slug_to_keyword(slug)
        source = "ebay" if slug.endswith("-ebay") else "amazon"
        amazon_cat = cat_by_keyword.get(keyword.lower(), "General")

        html = index_html.read_text(encoding="utf-8", errors="ignore")
        fallback = FALLBACK_MARKER in html

        learner.log(
            keyword=keyword, amazon_cat=amazon_cat, market="us",
            source=source, action="DEPLOYED", fallback=fallback,
            score=0.0, slug=slug,
        )
        count += 1

    print(f"✓ Bootstrap completo: {count} páginas registradas en {HISTORY_FILE}")
    print()
    print(learner.summary())


if __name__ == "__main__":
    main()
