# -*- coding: utf-8 -*-
"""
learning/find_thin_pages.py — Encuentra páginas generadas en modo fallback
(sin Claude, texto de plantilla genérico) y arma una cola de regeneración.

Corrí esto cuando recuperes crédito de Anthropic para saber exactamente
qué páginas re-generar primero (probablemente la razón #1 de que Google
solo indexe 11/282 páginas — ver LEARNING_SYSTEM.md).

Uso:
  python learning/find_thin_pages.py                 # solo lista y cuenta
  python learning/find_thin_pages.py --write-queue    # además escribe
                                                       # learning/regeneration_queue.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "docs"
QUEUE_FILE = Path(__file__).parent / "regeneration_queue.json"
FALLBACK_MARKER = "look for these three factors before committing to any"


def find_thin_pages() -> list[str]:
    thin = []
    for page_dir in sorted(DOCS_DIR.glob("best-*")):
        index_html = page_dir / "index.html"
        if not index_html.exists():
            continue
        html = index_html.read_text(encoding="utf-8", errors="ignore")
        if FALLBACK_MARKER in html:
            thin.append(page_dir.name.removeprefix("best-"))
    return thin


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-queue", action="store_true")
    args = parser.parse_args()

    slugs = find_thin_pages()
    total = len(list(DOCS_DIR.glob("best-*")))
    print(f"Páginas fallback (thin content): {len(slugs)} de {total} ({len(slugs)/total:.0%})")

    if args.write_queue:
        QUEUE_FILE.write_text(
            json.dumps({"pending_regeneration": slugs}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Cola escrita en {QUEUE_FILE} — {len(slugs)} slugs pendientes.")
    else:
        for s in slugs[:30]:
            print(f"  · {s}")
        if len(slugs) > 30:
            print(f"  … y {len(slugs) - 30} más (usa --write-queue para ver todas)")


if __name__ == "__main__":
    main()
