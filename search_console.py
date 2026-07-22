# -*- coding: utf-8 -*-
"""
search_console.py — Consulta el estado real de indexación de una URL en
Google mediante la Search Console API (urlInspection.index.inspect).

A diferencia de la Indexing API (que solo empuja un aviso "URL_UPDATED" sin
confirmar nada), esta API permite preguntarle a Google: "¿esta URL ya está
indexada?" — es la pieza que faltaba para poder medir progreso real hacia
la meta de páginas indexadas y decidir cuáles necesitan mejorarse.

Requiere:
  1. La "Google Search Console API" habilitada en el proyecto de GCP de la
     service account (GOOGLE_INDEXING_SA_JSON) — se habilita una sola vez
     desde https://console.cloud.google.com/apis/library/searchconsole.googleapis.com
  2. La service account agregada como usuario en la propiedad de Search
     Console (search.google.com/search-console → Configuración → Usuarios).

Si cualquiera de las dos cosas falta, todas las funciones devuelven None
silenciosamente (con un aviso una sola vez) para no romper el pipeline.
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SA_JSON_PATH = Path(os.getenv("GOOGLE_INDEXING_SA_JSON", "secrets/gcp-indexing-sa.json"))
SITE_URL     = os.getenv("SITE_URL", "https://trendvortex.tech").rstrip("/") + "/"
SCOPES       = ["https://www.googleapis.com/auth/webmasters.readonly"]

_service        = None
_disabled       = False
_warned_missing = False


def _get_service():
    """Crea (y cachea) el cliente de Search Console. None si no hay credenciales o la API está deshabilitada."""
    global _service, _disabled, _warned_missing
    if _disabled:
        return None
    if _service is not None:
        return _service
    if not SA_JSON_PATH.exists():
        if not _warned_missing:
            print(f"  [SEARCHCONSOLE] WARN: {SA_JSON_PATH} no encontrado - inspección desactivada")
            _warned_missing = True
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(str(SA_JSON_PATH), scopes=SCOPES)
        _service = build("searchconsole", "v1", credentials=creds)
    except Exception as e:
        print(f"  [SEARCHCONSOLE] ERROR inicializando cliente: {e}")
        _disabled = True
        return None
    return _service


def inspect_url(url: str) -> dict | None:
    """
    Consulta el estado de indexación de una URL.
    Retorna dict {"indexed": bool, "verdict": str, "coverage_state": str}
    o None si la consulta falló (API deshabilitada, sin permisos, red, etc.).
    """
    global _disabled
    service = _get_service()
    if service is None:
        return None

    try:
        resp = service.urlInspection().index().inspect(
            body={"inspectionUrl": url, "siteUrl": SITE_URL}
        ).execute()
    except Exception as e:
        msg = str(e)
        if "SERVICE_DISABLED" in msg or "has not been used" in msg:
            print("  [SEARCHCONSOLE] API deshabilitada en el proyecto de GCP — inspección desactivada hasta habilitarla")
            _disabled = True
        elif "PERMISSION_DENIED" in msg or "403" in msg:
            print("  [SEARCHCONSOLE] Sin permiso — agrega la service account como usuario en Search Console")
            _disabled = True
        else:
            print(f"  [SEARCHCONSOLE] ERROR inspeccionando {url}: {msg[:200]}")
        return None

    result = resp.get("inspectionResult", {})
    idx    = result.get("indexStatusResult", {})
    verdict         = idx.get("verdict", "UNKNOWN")
    coverage_state  = idx.get("coverageState", "")
    return {
        "indexed":        verdict == "PASS",
        "verdict":        verdict,
        "coverage_state": coverage_state,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for u in sys.argv[1:]:
            print(u, "->", inspect_url(u))
    else:
        print("Uso: python search_console.py <url1> [url2 ...]")
