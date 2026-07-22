# -*- coding: utf-8 -*-
"""
indexing_agent.py — Agente de indexación.

Objetivo: lograr que TODAS las páginas publicadas queden indexadas en
Google, a un ritmo de referencia de ~50 confirmaciones nuevas por día,
hasta cubrir el total.

Cada corrida:
  1. Detecta páginas publicadas nuevas (docs/*/index.html) y las registra.
  2. Notifica a la Indexing API las que aún no se hayan notificado nunca
     (delegado en indexing_api.notify_backlog).
  3. Inspecciona con Search Console las páginas que aún no están confirmadas
     como indexadas (si la API de Search Console no está habilitada, este
     paso se salta solo, sin romper nada).
  4. Para páginas notificadas hace ≥ IMPROVE_AFTER_DAYS días y que Google
     todavía no indexó (o no se pudo confirmar), usa Claude para reescribir
     la página, la redespliega y la vuelve a notificar.
  5. Reporta avance: cuántas confirmadas indexadas hoy vs. la meta diaria,
     y cuántas quedan pendientes del total.

Estado persistido en indexing_status.json:
  {slug: {status, last_checked, notified_at, improved_count, first_seen}}
"""
from __future__ import annotations
import json, subprocess
from pathlib import Path
from datetime import datetime, timedelta

from indexing_api import notify_backlog, notify_url, DAILY_QUOTA
import search_console
from page_improver import improve_page

DOCS_DIR       = Path("docs")
STATUS_FILE    = Path("indexing_status.json")
SITE_URL_ENV   = __import__("os").getenv("SITE_URL", "https://trendvortex.tech").rstrip("/")

DAILY_GOAL           = 50   # meta de páginas nuevas confirmadas indexadas / día
MAX_CHECKS_PER_RUN   = 60   # tope de consultas a Search Console por corrida (cuota API)
IMPROVE_AFTER_DAYS   = 4    # días de gracia tras notificar antes de intentar mejorar
MAX_IMPROVE_ATTEMPTS = 2    # tope de reescrituras por página (costo Claude)
MAX_IMPROVE_PER_RUN  = 15   # tope de páginas a mejorar por corrida


def _load_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_status(status: dict):
    STATUS_FILE.write_text(json.dumps(status, indent=1), encoding="utf-8")


def _all_slugs() -> list[str]:
    return sorted(p.parent.name for p in DOCS_DIR.glob("*/index.html") if p.parent != DOCS_DIR)


def _url_for(slug: str) -> str:
    return f"{SITE_URL_ENV}/{slug}/"


def _days_since(iso_ts: str | None) -> float:
    if not iso_ts:
        return 999.0
    try:
        return (datetime.now() - datetime.fromisoformat(iso_ts)).total_seconds() / 86400
    except Exception:
        return 999.0


def deploy_improved(slugs: list[str]):
    if not slugs:
        return
    try:
        subprocess.run(["git", "add", "-f", "docs/"], check=True)
        subprocess.run(["git", "commit", "-m", f"[IndexingAgent] mejora SEO en {len(slugs)} página(s)"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"  [INDEXING-AGENT] {len(slugs)} página(s) mejorada(s) redesplegadas")
    except subprocess.CalledProcessError as e:
        print(f"  [INDEXING-AGENT] Error git: {e}")


def run() -> dict:
    now_iso = datetime.now().isoformat()
    status  = _load_status()
    slugs   = _all_slugs()

    # 1) Registrar páginas nuevas
    for slug in slugs:
        if slug not in status:
            status[slug] = {
                "status": "unknown", "last_checked": None,
                "notified_at": None, "improved_count": 0, "first_seen": now_iso,
            }

    # 2) Notificar backlog no notificado (respeta cuota diaria compartida)
    urls = [_url_for(s) for s in slugs]
    notify_backlog(urls)

    # Marcar notified_at para las que sí quedaron en indexing_notified.json
    try:
        notified_urls = set(json.loads(Path("indexing_notified.json").read_text(encoding="utf-8")))
    except Exception:
        notified_urls = set()
    for slug in slugs:
        if _url_for(slug) in notified_urls and status[slug]["notified_at"] is None:
            status[slug]["notified_at"] = now_iso

    # 3) Inspeccionar (Search Console) las que aún no están confirmadas indexadas
    pending = [s for s in slugs if status[s]["status"] != "indexed"]
    pending.sort(key=lambda s: status[s]["last_checked"] or "")
    checked_today = 0
    for slug in pending[:MAX_CHECKS_PER_RUN]:
        result = search_console.inspect_url(_url_for(slug))
        if result is None:
            break  # API deshabilitada/sin permiso — no seguir gastando llamadas
        status[slug]["last_checked"] = now_iso
        status[slug]["status"] = "indexed" if result["indexed"] else "not_indexed"
        checked_today += 1

    indexed_total = sum(1 for s in status.values() if s["status"] == "indexed")

    # 4) Mejorar con Claude las que llevan tiempo notificadas y no indexan
    candidates = [
        slug for slug in slugs
        if status[slug]["status"] != "indexed"
        and status[slug]["notified_at"] is not None
        and _days_since(status[slug]["notified_at"]) >= IMPROVE_AFTER_DAYS
        and status[slug]["improved_count"] < MAX_IMPROVE_ATTEMPTS
    ]
    candidates = candidates[:MAX_IMPROVE_PER_RUN]

    improved_slugs = []
    for slug in candidates:
        if improve_page(slug):
            status[slug]["improved_count"] += 1
            status[slug]["notified_at"] = now_iso  # reinicia el plazo de gracia
            status[slug]["status"] = "unknown"      # a reconfirmar en próxima corrida
            improved_slugs.append(slug)

    if improved_slugs:
        deploy_improved(improved_slugs)
        notify_url_urls = [_url_for(s) for s in improved_slugs]
        for u in notify_url_urls:
            notify_url(u, type_="URL_UPDATED")

    _save_status(status)

    summary = {
        "total_pages":     len(slugs),
        "indexed_total":   indexed_total,
        "pending":         len(slugs) - indexed_total,
        "checked_today":   checked_today,
        "improved_today":  len(improved_slugs),
        "daily_goal":      DAILY_GOAL,
    }
    print(
        f"  [INDEXING-AGENT] {indexed_total}/{len(slugs)} indexadas confirmadas "
        f"(meta ritmo: {DAILY_GOAL}/día) · {checked_today} chequeadas hoy · "
        f"{len(improved_slugs)} mejoradas hoy"
    )
    return summary


if __name__ == "__main__":
    run()
