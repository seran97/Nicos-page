# -*- coding: utf-8 -*-
"""
pinterest_poster.py — Publica un Pin automáticamente por cada página nueva
que despliega el orquestador, usando la Pinterest API v5.

Requiere en .env:
  PINTEREST_ACCESS_TOKEN=pina_...
  PINTEREST_BOARD_ID=...        (opcional — si falta, se autodetecta el
                                  primer tablero de la cuenta y se cachea aquí)
  PINTEREST_SANDBOX=1           (mientras la app solo tiene "Trial access" —
                                  los pines van al entorno de pruebas de
                                  Pinterest, invisibles al público. Quitar/
                                  poner en 0 en cuanto aprueben Standard access)

Si el token no está configurado, todas las funciones devuelven False/None
silenciosamente (con un aviso una sola vez) para no romper el pipeline
principal — igual que search_console.py.
"""
from __future__ import annotations
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_BASE = (
    "https://api-sandbox.pinterest.com/v5"
    if os.getenv("PINTEREST_SANDBOX", "0") == "1"
    else "https://api.pinterest.com/v5"
)
ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "")
ENV_PATH = Path(__file__).resolve().parent / ".env"

_board_id_cache: str | None = os.getenv("PINTEREST_BOARD_ID") or None
_warned_missing = False


def _headers() -> dict:
    return {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}


def _get_board_id() -> str | None:
    """Devuelve el board_id a usar — cacheado en memoria y persistido al .env."""
    global _board_id_cache
    if _board_id_cache:
        return _board_id_cache
    try:
        r = requests.get(f"{API_BASE}/boards", headers=_headers(), timeout=15)
        if r.status_code != 200:
            print(f"  [Pinterest] ERROR listando tableros: HTTP {r.status_code} {r.text[:150]}")
            return None
        items = r.json().get("items", [])
        if not items:
            print("  [Pinterest] No hay tableros en la cuenta — crea uno en pinterest.com primero")
            return None
        _board_id_cache = items[0]["id"]
        _persist_board_id(_board_id_cache)
        return _board_id_cache
    except Exception as e:
        print(f"  [Pinterest] ERROR obteniendo tablero: {e}")
        return None


def _persist_board_id(board_id: str):
    """Guarda PINTEREST_BOARD_ID en .env para no volver a listarlo cada vez."""
    try:
        if not ENV_PATH.exists():
            return
        text = ENV_PATH.read_text(encoding="utf-8")
        if "PINTEREST_BOARD_ID=" in text:
            return  # ya seteado por el usuario, no lo pisamos
        with ENV_PATH.open("a", encoding="utf-8") as f:
            f.write(f"\nPINTEREST_BOARD_ID={board_id}\n")
    except Exception:
        pass


def create_pin(page_url: str, image_url: str, title: str, description: str) -> bool:
    """
    Crea un Pin enlazando a `page_url` con `image_url` como imagen.
    Devuelve True si se publicó, False si algo falló (nunca lanza excepción).
    """
    global _warned_missing
    if not ACCESS_TOKEN:
        if not _warned_missing:
            print("  [Pinterest] WARN: PINTEREST_ACCESS_TOKEN no configurado — publicación desactivada")
            _warned_missing = True
        return False
    if not image_url:
        print("  [Pinterest] Skip: sin imagen de producto")
        return False

    board_id = _get_board_id()
    if not board_id:
        return False

    payload = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:500],
        "link": page_url,
        "media_source": {"source_type": "image_url", "url": image_url},
    }

    try:
        r = requests.post(f"{API_BASE}/pins", headers=_headers(), json=payload, timeout=20)
        if r.status_code in (200, 201):
            pin_url = r.json().get("id", "")
            print(f"  [Pinterest] OK Pin creado ({pin_url}) -> {page_url}")
            return True
        print(f"  [Pinterest] ERROR HTTP {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"  [Pinterest] ERROR creando pin: {e}")
        return False
