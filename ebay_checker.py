# -*- coding: utf-8 -*-
"""
ebay_checker.py — Búsqueda de productos eBay + links de afiliado EPN

Credenciales necesarias:
  EBAY_SID      = SID de cuenta (del portal EPN → Credenciales de API), usado
                  para armar el link de afiliado rover.
  EBAY_APP_ID   = App ID / Client ID (de developer.ebay.com → Application Keys)
  EBAY_CERT_ID  = Cert ID / Client Secret (misma pantalla que el App ID)

La búsqueda de productos usa la Browse API moderna de eBay (REST + OAuth2
client-credentials). La antigua Finding API (svcs.ebay.com) fue descontinuada
para apps nuevas — devuelve 503 aunque el App ID sea válido. Si no hay
App ID + Cert ID, cae a scraping liviano del feed RSS público de eBay.
"""
from __future__ import annotations
import os, time, re, base64
from typing import Optional
from urllib.parse import quote_plus
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Credenciales EPN (para el link de afiliado) ──────────────────────────────
EBAY_SID    = os.getenv("EBAY_SID", "")        # SID de cuenta
EBAY_TOKEN  = os.getenv("EBAY_TOKEN", "")      # Token de autenticación (no usado en Browse API)

# Credenciales OAuth2 de developer.ebay.com → Application Keys (Production)
EBAY_APP_ID  = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID", "")

EBAY_SITE   = os.getenv("EBAY_SITE", "EBAY-US")
PRICE_MIN   = 20.0
PRICE_MAX   = 200.0

_cache: dict[str, Optional[dict]] = {}
_oauth_token: dict = {"value": "", "expires_at": 0}


# ── OAuth2 client-credentials (Browse API) ───────────────────────────────────

def _get_oauth_token() -> Optional[str]:
    """Obtiene (y cachea) un access token de aplicación vía client_credentials."""
    if _oauth_token["value"] and time.time() < _oauth_token["expires_at"] - 60:
        return _oauth_token["value"]
    if not (EBAY_APP_ID and EBAY_CERT_ID):
        return None
    try:
        creds = base64.b64encode(f"{EBAY_APP_ID}:{EBAY_CERT_ID}".encode()).decode()
        r = requests.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
            headers={
                "Content-Type":  "application/x-www-form-urlencoded",
                "Authorization": f"Basic {creds}",
            },
            data={
                "grant_type": "client_credentials",
                "scope":      "https://api.ebay.com/oauth/api_scope",
            },
            timeout=15,
        )
        if r.status_code != 200:
            print(f"  [eBay OAuth] Error {r.status_code}: {r.text[:200]}")
            return None
        data = r.json()
        _oauth_token["value"] = data["access_token"]
        _oauth_token["expires_at"] = time.time() + int(data.get("expires_in", 7200))
        return _oauth_token["value"]
    except Exception as e:
        print(f"  [eBay OAuth] Error: {e}")
        return None


# ── Link de afiliado rover ────────────────────────────────────────────────────

def _rover_link(item_url: str) -> str:
    """
    Convierte URL de eBay en link de afiliado usando EPN rover.
    Solo necesita el SID (= campaign/publisher ID en el rover link).
    """
    if not EBAY_SID:
        return item_url
    encoded = quote_plus(item_url)
    # Formato rover EPN estándar con SID como campid
    return (
        f"https://rover.ebay.com/rover/1/711-53200-19255-0/1"
        f"?campid={EBAY_SID}&toolid=10001&customid=trendvortex"
        f"&mpre={encoded}"
    )


# ── Búsqueda con Browse API (OAuth2, requiere App ID + Cert ID) ──────────────

def _search_finding_api(keyword: str) -> Optional[dict]:
    """Usa la Browse API de eBay (requiere EBAY_APP_ID + EBAY_CERT_ID)."""
    token = _get_oauth_token()
    if not token:
        return None
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    params = {
        "q":       keyword,
        "filter":  f"price:[{PRICE_MIN}..{PRICE_MAX}],priceCurrency:USD,conditions:{{NEW}}",
        "sort":    "price",
        "limit":   "10",
    }
    headers = {
        "Authorization":                  f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID":        EBAY_SITE,
        "X-EBAY-C-ENDUSERCTX":            "affiliateCampaignId=,affiliateReferenceId=",
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"  [eBay Browse] Error {r.status_code}: {r.text[:200]}")
            return None
        items = r.json().get("itemSummaries", [])
        for item in items:
            try:
                precio = float(item["price"]["value"])
                if not (PRICE_MIN <= precio <= PRICE_MAX):
                    continue
                titulo   = item["title"]
                item_url = item["itemWebUrl"]
                imagen   = (item.get("image") or {}).get("imageUrl", "")
                return {
                    "titulo":        titulo,
                    "precio":        round(precio, 2),
                    "rating":        4.2,          # Browse API no da rating de producto
                    "reviews":       max(50, int(item.get("estimatedAvailabilities", [{}])[0]
                                                  .get("estimatedAvailableQuantity", 50))
                                          if item.get("estimatedAvailabilities") else 50),
                    "imagen_url":    imagen,
                    "affiliate_url": _rover_link(item_url),
                    "source":        "ebay",
                }
            except (KeyError, IndexError, TypeError, ValueError):
                continue
    except Exception as e:
        print(f"  [eBay Browse] Error: {e}")
    return None


# ── Búsqueda con RSS público (sin credenciales extra) ─────────────────────────

def _search_rss(keyword: str) -> Optional[dict]:
    """
    Usa el feed RSS público de eBay — sin App ID, sin auth.
    Limitado a 25 resultados pero suficiente para validar.
    """
    encoded = quote_plus(keyword)
    # RSS feed de eBay con filtros de precio
    rss_url = (
        f"https://www.ebay.com/sch/i.html?_nkw={encoded}"
        f"&_sop=12&LH_BIN=1&LH_ItemCondition=3&rt=nc"
        f"&_udlo={int(PRICE_MIN)}&_udhi={int(PRICE_MAX)}"
        f"&_rss=1"
    )
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TrendVortex/1.0)"}
        r = requests.get(rss_url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None

        # Parsear RSS simple con regex (sin dependencia xml)
        items_raw = re.findall(r"<item>(.*?)</item>", r.text, re.DOTALL)
        for raw in items_raw[:8]:
            try:
                titulo = re.search(r"<title><!\[CDATA\[(.*?)\]\]>", raw)
                link   = re.search(r"<link>(.*?)</link>", raw)
                precio_m = re.search(r"\$([0-9]+\.?[0-9]*)", raw)

                if not titulo or not link or not precio_m:
                    continue

                precio = float(precio_m.group(1))
                if not (PRICE_MIN <= precio <= PRICE_MAX):
                    continue

                item_url = link.group(1).strip()
                # Limpiar URL eBay (quitar parámetros de tracking internos)
                item_url = re.sub(r"\?.*$", "", item_url) + "?mkevt=1"

                return {
                    "titulo":        titulo.group(1).strip(),
                    "precio":        round(precio, 2),
                    "rating":        4.1,
                    "reviews":       50,
                    "imagen_url":    "",
                    "affiliate_url": _rover_link(item_url),
                    "source":        "ebay",
                }
            except (AttributeError, ValueError):
                continue
    except Exception as e:
        print(f"  [eBay RSS] Error: {e}")
    return None


# ── Interfaz pública ──────────────────────────────────────────────────────────

def check_ebay(keyword: str) -> Optional[dict]:
    """
    Busca producto en eBay. Intenta Finding API primero (si hay App ID),
    luego RSS público.
    """
    if keyword in _cache:
        return _cache[keyword]

    result = None
    if EBAY_APP_ID and EBAY_CERT_ID:
        result = _search_finding_api(keyword)
    if not result:
        result = _search_rss(keyword)

    _cache[keyword] = result
    return result


def check_product(keyword: str) -> Optional[dict]:
    """
    Multi-source: Amazon (Rainforest) → eBay fallback.
    Importado por el orchestrator.
    """
    try:
        from amazon_checker import check_amazon
        result = check_amazon(keyword)
        if result:
            result["source"] = "amazon"
            return result
    except Exception as e:
        print(f"  [Checker] Amazon: {e}")

    result = check_ebay(keyword)
    if result:
        print(f"  [Checker] eBay fallback OK para '{keyword}'")
    return result


# ── Test rápido ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    from dotenv import load_dotenv
    load_dotenv()

    kw = sys.argv[1] if len(sys.argv) > 1 else "sous vide cooker"
    print(f"Buscando '{kw}' en eBay...")
    r = check_ebay(kw)
    if r:
        print(f"  ✓ {r['titulo'][:60]}")
        print(f"  $ {r['precio']} | {r['rating']}★")
        print(f"  🔗 {r['affiliate_url'][:80]}")
    else:
        print("  ✗ Sin resultado")
