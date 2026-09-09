# -*- coding: utf-8 -*-
"""
rss_feed_reader.py — Lee docs/rss.xml (generado por
page_generator.py::actualizar_rss()) con feedparser y detecta entradas
nuevas/no procesadas todavía, comparando contra un estado local persistido
en rss_reader_state.json.

Este es el "Fase 1: RSS + IA" del plan de automatización multi-canal — el
sitio se vuelve su propia fuente de la verdad (data contract) para lo que
hay publicado, en vez de que cada integración (newsletter, redes) tenga
que re-escanear docs/ a mano con su propia lógica.

Uso:
  python rss_feed_reader.py              # imprime entradas nuevas, las marca como vistas
  python rss_feed_reader.py --dry-run    # solo imprime, no marca nada como procesado
  python rss_feed_reader.py --reset      # borra el estado (vuelve a tratar todo como nuevo)

Uso programático (ej. desde un futuro script de newsletter):
  from rss_feed_reader import get_new_entries
  nuevas = get_new_entries()   # marca como vistas al llamar
  for e in nuevas:
      ...
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import feedparser

RSS_PATH   = Path("docs/rss.xml")
STATE_FILE = Path("rss_reader_state.json")


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_feed() -> list[dict]:
    """Parsea docs/rss.xml y devuelve las entradas como dicts simples
    {guid, title, link, description, published}. No requiere red — lee el
    archivo local generado en el mismo build."""
    if not RSS_PATH.exists():
        print(f"  [RSS] {RSS_PATH} no existe todavía — corré actualizar_rss() primero")
        return []
    d = feedparser.parse(str(RSS_PATH))
    if d.bozo:
        print(f"  [RSS] WARN: el feed tiene errores de formato ({d.bozo_exception})")
    entries = []
    for e in d.entries:
        entries.append({
            "guid": e.get("id") or e.get("link"),
            "title": e.get("title", ""),
            "link": e.get("link", ""),
            "description": e.get("summary", ""),
            "published": e.get("published", ""),
        })
    return entries


def get_new_entries(mark_seen: bool = True) -> list[dict]:
    """Devuelve las entradas del feed que todavía no estaban en el estado
    local (o sea: nuevas desde la última vez que se llamó esta función).
    Si mark_seen=True (default), las marca como vistas antes de devolver."""
    entries = parse_feed()
    state = _load_state()
    now_iso = datetime.now(timezone.utc).isoformat()

    new_entries = [e for e in entries if e["guid"] not in state]

    if mark_seen:
        for e in new_entries:
            state[e["guid"]] = {"first_seen": now_iso, "title": e["title"]}
        _save_state(state)

    return new_entries


def main():
    parser = argparse.ArgumentParser(description="Detecta contenido nuevo en docs/rss.xml")
    parser.add_argument("--dry-run", action="store_true",
                         help="Solo imprime las entradas nuevas, no las marca como procesadas")
    parser.add_argument("--reset", action="store_true",
                         help="Borra el estado local (todo vuelve a contar como nuevo)")
    args = parser.parse_args()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("  [RSS] Estado reiniciado")
        return

    new_entries = get_new_entries(mark_seen=not args.dry_run)

    if not new_entries:
        print("  [RSS] Sin entradas nuevas")
        return

    print(f"  [RSS] {len(new_entries)} entrada(s) nueva(s):")
    for e in new_entries:
        print(f"   - {e['title'][:60]}  ->  {e['link']}")


if __name__ == "__main__":
    main()
