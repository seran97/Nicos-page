# -*- coding: utf-8 -*-
"""
indexing_api.py — Notifica a Google (Indexing API) cuando se publican
páginas nuevas o actualizadas, para acelerar el rastreo/indexación.

Requiere una service account de Google Cloud con rol "Propietario" en la
propiedad de Search Console del sitio. Ruta al JSON vía variable de entorno
GOOGLE_INDEXING_SA_JSON (ver .env).

Si no hay credenciales configuradas todavía, todas las funciones se saltan
silenciosamente (con un aviso una sola vez) para no romper el pipeline.

Nota: la Indexing API está documentada oficialmente solo para páginas de
tipo JobPosting/BroadcastEvent. Para contenido general (nuestro caso) Google
la acepta sin error pero no garantiza indexación más rápida por este medio,
y el uso fuera de esos tipos de contenido puede llevar a revocar el acceso
si se abusa del volumen. Por eso el límite diario por defecto (190) queda
por debajo de la cuota real (200) y se mantiene conservador.
"""
from __future__ import annotations
import os, json, time
from pathlib import Path
from datetime import date, datetime, timezone
from dotenv import load_dotenv

load_dotenv()

INDEXING_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"
SCOPES            = ["https://www.googleapis.com/auth/indexing"]

SA_JSON_PATH   = Path(os.getenv("GOOGLE_INDEXING_SA_JSON", "secrets/gcp-indexing-sa.json"))
QUOTA_FILE     = Path(os.getenv("INDEXING_QUOTA_FILE", "indexing_quota.json"))
DAILY_QUOTA    = int(os.getenv("INDEXING_DAILY_QUOTA", "190"))
NOTIFIED_FILE  = Path(os.getenv("INDEXING_NOTIFIED_FILE", "indexing_notified.json"))

_credentials     = None
_warned_missing  = False


def _get_credentials():
    """Carga (y cachea) las credenciales de la service account. None si no hay o falla."""
    global _credentials, _warned_missing
    if _credentials is not None:
        return _credentials
    if not SA_JSON_PATH.exists():
        if not _warned_missing:
            print(f"  [INDEXING] WARN: {SA_JSON_PATH} no encontrado - Indexing API desactivada")
            _warned_missing = True
        return None
    try:
        from google.oauth2 import service_account
        _credentials = service_account.Credentials.from_service_account_file(
            str(SA_JSON_PATH), scopes=SCOPES
        )
    except Exception as e:
        print(f"  [INDEXING] ERROR cargando credenciales: {e}")
        _credentials = None
    return _credentials


def _load_quota() -> dict:
    today = date.today().isoformat()
    if QUOTA_FILE.exists():
        try:
            data = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
            if data.get("date") == today:
                return data
        except Exception:
            pass
    return {"date": today, "count": 0}


def _save_quota(data: dict):
    QUOTA_FILE.write_text(json.dumps(data), encoding="utf-8")


def _load_notified() -> set[str]:
    """URLs que ya se enviaron alguna vez a la Indexing API (histórico, no por día)."""
    if NOTIFIED_FILE.exists():
        try:
            return set(json.loads(NOTIFIED_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def _save_notified(notified: set[str]):
    NOTIFIED_FILE.write_text(json.dumps(sorted(notified)), encoding="utf-8")


def notify_url(url: str, type_: str = "URL_UPDATED") -> bool:
    """Notifica una URL individual a la Indexing API. Retorna True si Google la aceptó (HTTP 200)."""
    creds = _get_credentials()
    if creds is None:
        return False

    quota = _load_quota()
    if quota["count"] >= DAILY_QUOTA:
        print(f"  [INDEXING] Cuota diaria alcanzada ({DAILY_QUOTA}/dia) - se salta {url}")
        return False

    import requests
    from google.auth.transport.requests import Request as GoogleAuthRequest

    if not creds.valid:
        creds.refresh(GoogleAuthRequest())

    try:
        resp = requests.post(
            INDEXING_ENDPOINT,
            headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
            json={"url": url, "type": type_},
            timeout=15,
        )
    except requests.RequestException as e:
        print(f"  [INDEXING] ERROR de red notificando {url}: {e}")
        return False

    quota["count"] += 1
    _save_quota(quota)

    if resp.status_code == 200:
        notified = _load_notified()
        notified.add(url)
        _save_notified(notified)
        print(f"  [INDEXING] OK {url}")
        return True

    print(f"  [INDEXING] ERROR {resp.status_code} notificando {url}: {resp.text[:200]}")
    return False


def notify_urls(urls: list[str], type_: str = "URL_UPDATED") -> int:
    """Notifica una lista de URLs (con pausa de 1s entre llamadas). Retorna cuántas se aceptaron."""
    if not urls or _get_credentials() is None:
        return 0
    ok = 0
    for url in urls:
        if notify_url(url, type_=type_):
            ok += 1
        time.sleep(1)
    print(f"  [INDEXING] {ok}/{len(urls)} URLs notificadas a Google")
    return ok


def notify_backlog(all_urls: list[str], type_: str = "URL_UPDATED") -> int:
    """
    Recorre TODAS las páginas ya publicadas (backlog histórico, ej. las 398
    generadas antes de tener esta integración) y notifica las que todavía no
    se han enviado nunca a la Indexing API, respetando la cuota diaria
    restante. Pensado para llamarse en cada ciclo del orquestador: como la
    cuota es compartida con `notify_urls` (páginas nuevas), el backlog se va
    consumiendo en el margen que quede libre cada día hasta ponerse al día.
    """
    if _get_credentials() is None:
        return 0

    notified = _load_notified()
    pending = [u for u in all_urls if u not in notified]
    if not pending:
        return 0

    quota = _load_quota()
    remaining = DAILY_QUOTA - quota["count"]
    if remaining <= 0:
        print(f"  [INDEXING] Cuota diaria agotada — backlog espera ({len(pending)} URLs pendientes)")
        return 0

    batch = pending[:remaining]
    print(f"  [INDEXING] Backlog: {len(pending)} URLs sin notificar — enviando {len(batch)} (cuota restante {remaining})")
    ok = 0
    for url in batch:
        if notify_url(url, type_=type_):
            ok += 1
        time.sleep(1)
    print(f"  [INDEXING] Backlog: {ok}/{len(batch)} notificadas — quedan {len(pending) - ok} en cola")
    return ok


if __name__ == "__main__":
    # Test manual: python indexing_api.py https://trendvortex.tech/best-ejemplo/
    import sys
    if len(sys.argv) > 1:
        notify_urls(sys.argv[1:])
    else:
        print("Uso: python indexing_api.py <url1> [url2 ...]")
