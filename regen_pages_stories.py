# -*- coding: utf-8 -*-
"""
regen_pages_stories.py — Regenera páginas EXISTENTES con Claude (no template
fallback) para que incluyan la nueva sección "Real story" (anécdota personal,
ver agents/designer_agent.py). A diferencia de regen_pages.py (que solo
reaplica el template estático), esto SÍ llama a la API de Claude por página
— tiene costo y está rate-limited a propósito.

Uso:
  python regen_pages_stories.py --limit 20      # piloto
  python regen_pages_stories.py                 # todas las que falten
  python regen_pages_stories.py --resume-from best-air-fryer
"""
from __future__ import annotations
import sys, os, re, json, time, argparse
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from dotenv import load_dotenv
load_dotenv()

from agents.designer_agent import DesignerAgent
from regen_pages import extract_from_html

DOCS_DIR = Path("docs")
SECONDS_BETWEEN_CALLS = 90  # ~40/hora, deja margen para el swarm normal
PROGRESS_FILE = Path("regen_stories_progress.txt")


def _source_from_dirname(name: str) -> str:
    if name.endswith("-ebay"):
        return "ebay"
    if name.endswith("-aliexpress"):
        return "aliexpress"
    return "amazon"


def _keyword_from_dirname(name: str) -> str:
    kw = name.removeprefix("best-")
    kw = re.sub(r"-(ebay|aliexpress)$", "", kw)
    return kw.replace("-", " ")


def _cargar_progreso() -> set[str]:
    if PROGRESS_FILE.exists():
        return set(PROGRESS_FILE.read_text(encoding="utf-8").splitlines())
    return set()


def _marcar_hecho(name: str):
    with PROGRESS_FILE.open("a", encoding="utf-8") as f:
        f.write(name + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = sin límite")
    args = ap.parse_args()

    designer = DesignerAgent()
    hecho = _cargar_progreso()

    page_dirs = sorted(
        d for d in DOCS_DIR.iterdir()
        if d.is_dir() and (d / "index.html").exists() and d.name not in hecho
    )
    if args.limit:
        page_dirs = page_dirs[:args.limit]

    print(f"Regenerando {len(page_dirs)} páginas con Claude (sección historia)...")
    print(f"Ritmo: 1 cada {SECONDS_BETWEEN_CALLS}s (~{3600//SECONDS_BETWEEN_CALLS}/hora)\n")

    ok = fallback_count = skip = 0

    for i, page_dir in enumerate(page_dirs, 1):
        name = page_dir.name
        html_text = (page_dir / "index.html").read_text(encoding="utf-8", errors="replace")
        data = extract_from_html(html_text)
        if not data or not data["titulo"]:
            print(f"  [{i}/{len(page_dirs)}] SKIP {name} — sin datos de producto")
            skip += 1
            _marcar_hecho(name)
            continue

        keyword = _keyword_from_dirname(name)
        source  = _source_from_dirname(name)

        context = {
            "keyword": keyword,
            "amazon": {
                "titulo":       data["titulo"],
                "precio":       data["precio"],
                "rating":       data["rating"],
                "reviews":      data["reviews"],
                "imagen_url":   data["imagen_url"],
                "affiliate_url": data["affiliate_url"],
                "source":       source,
            },
            "trend_payload": {},
            "subreddit":  data["subreddit"],
            "amazon_cat": data["amazon_cat"] or "General",
            "seo_content": {},
        }

        try:
            result = designer.act(context)
            fallback = result.payload.get("fallback", False)
            tag = "FALLBACK (sin Claude)" if fallback else "OK con historia"
            print(f"  [{i}/{len(page_dirs)}] {tag} — {name}")
            if fallback:
                fallback_count += 1
            else:
                ok += 1
        except Exception as e:
            print(f"  [{i}/{len(page_dirs)}] ERROR {name}: {e}")

        _marcar_hecho(name)

        if i < len(page_dirs):
            time.sleep(SECONDS_BETWEEN_CALLS)

    print(f"\n{'='*50}")
    print(f"  Regeneradas con historia: {ok} | Fallback: {fallback_count} | Saltadas: {skip}")
    print(f"  Falta hacer 'git add docs && git commit && git push' para publicar")


if __name__ == "__main__":
    main()
