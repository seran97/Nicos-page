# -*- coding: utf-8 -*-
"""
learning/apply_copy.py — Aplica los archivos learning/copy_batches/copy_*.json
a las paginas fallback correspondientes usando inject_copy.py, y marca en
history.jsonl que esas paginas ya fueron regeneradas con copy original.

Uso:
  python learning/apply_copy.py
"""
from __future__ import annotations

import json
from pathlib import Path

from inject_copy import inject
from niche_learner import NicheLearner

BATCHES_DIR = Path(__file__).parent / "copy_batches"


def main():
    learner = NicheLearner()
    total_ok, total_fail = 0, 0
    for batch_file in sorted(BATCHES_DIR.glob("copy_*.json")):
        items = json.loads(batch_file.read_text(encoding="utf-8"))
        for item in items:
            slug = item["slug"]
            ok = inject(slug, item)
            if ok:
                total_ok += 1
                learner.log(
                    keyword=slug.replace("-", " "), amazon_cat="General",
                    market="us", source="amazon", action="REGENERATED",
                    fallback=False, score=0.0, slug=slug,
                )
            else:
                total_fail += 1
                print(f"  ! No se encontro pagina para slug: {slug}")
        print(f"{batch_file.name}: procesado")

    print(f"\nTotal aplicado: {total_ok} paginas OK, {total_fail} no encontradas")


if __name__ == "__main__":
    main()
