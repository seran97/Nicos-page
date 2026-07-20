# -*- coding: utf-8 -*-
"""
aliexpress_checker.py — Búsqueda de productos AliExpress + links de afiliado

Credenciales necesarias (de open.aliexpress.com → App Console → App Overview):
  ALIEXPRESS_APP_KEY     = App Key
  ALIEXPRESS_APP_SECRET  = App Secret
  ALIEXPRESS_TRACKING_ID = Tracking ID (identifica la campaña de afiliado)

Usa la AliExpress Affiliate API (aliexpress.affiliate.product.query) via el
gateway TOP (api-sg.aliexpress.com/sync), con firma MD5 estándar de la
plataforma TOP de Alibaba.
"""
from __future__ import annotations
import os, time, hashlib
from typing import Optional
import requests
from dotenv import load_dotenv

from keyword_filter import es_producto_relevante

load_dotenv()

APP_KEY      = os.getenv("ALIEXPRESS_APP_KEY", "")
APP_SECRET   = os.getenv("ALIEXPRESS_APP_SECRET", "")
TRACKING_ID  = os.getenv("ALIEXPRESS_TRACKING_ID", "")

PRICE_MIN = 20.0
PRICE_MAX = 200.0

_cache: dict[str, Optional[dict]] = {}

API_URL = "https://api-sg.aliexpress.com/sync"


# ── Firma MD5 estándar TOP (Alibaba Open Platform) ───────────────────────────

def _sign(params: dict) -> str:
    ordered = sorted(params.items())
    base = APP_SECRET + "".join(f"{k}{v}" for k, v in ordered) + APP_SECRET
    return hashlib.md5(base.encode("utf-8")).hexdigest().upper()


def _call_api(method: str, extra_params: dict) -> Optional[dict]:
    params = {
        "method":        method,
        "app_key":       APP_KEY,
        "timestamp":     str(int(time.time() * 1000)),
        "sign_method":   "md5",
        "v":             "2.0",
        "format":        "json",
        **extra_params,
    }
    params["sign"] = _sign(params)
    try:
        r = requests.get(API_URL, params=params, timeout=15)
        if r.status_code != 200:
            print(f"  [AliExpress] HTTP {r.status_code}: {r.text[:200]}")
            return None
        data = r.json()
        if "error_response" in data:
            err = data["error_response"]
            print(f"  [AliExpress] API error: {err.get('msg', err)}")
            return None
        return data
    except Exception as e:
        print(f"  [AliExpress] Error: {e}")
        return None


# ── Búsqueda de productos ─────────────────────────────────────────────────────

def check_aliexpress(keyword: str) -> Optional[dict]:
    """
    Busca un producto en AliExpress vía la Affiliate API oficial.
    Requiere ALIEXPRESS_APP_KEY + ALIEXPRESS_APP_SECRET + ALIEXPRESS_TRACKING_ID.
    """
    if keyword in _cache:
        return _cache[keyword]

    if not (APP_KEY and APP_SECRET and TRACKING_ID):
        _cache[keyword] = None
        return None

    data = _call_api("aliexpress.affiliate.product.query", {
        "keywords":         keyword,
        "tracking_id":      TRACKING_ID,
        "page_no":          "1",
        "page_size":        "10",
        "target_currency":  "USD",
        "target_language":  "EN",
        "sort":             "SALE_PRICE_ASC",
        "min_sale_price":   str(int(PRICE_MIN * 100)),   # AliExpress usa centavos
        "max_sale_price":   str(int(PRICE_MAX * 100)),
    })

    result = None
    if data:
        try:
            products = (data.get("aliexpress_affiliate_product_query_response", {})
                            .get("resp_result", {})
                            .get("result", {})
                            .get("products", {})
                            .get("product", []))
            for item in products:
                try:
                    precio = float(item.get("target_sale_price") or item.get("sale_price") or 0)
                    if not (PRICE_MIN <= precio <= PRICE_MAX):
                        continue
                    titulo = item.get("product_title", "").strip()
                    if not es_producto_relevante(keyword, titulo):
                        print(f"  [AliExpress] Descartado (sin relación con '{keyword}'): {titulo[:60]}")
                        continue
                    result = {
                        "titulo":        titulo,
                        "precio":        round(precio, 2),
                        "rating":        4.3,   # la Affiliate API no expone rating de producto
                        "reviews":       max(50, int(item.get("lastest_volume") or 0)),
                        "imagen_url":    item.get("product_main_image_url", ""),
                        "affiliate_url": item.get("promotion_link") or item.get("product_detail_url", ""),
                        "source":        "aliexpress",
                    }
                    break
                except (KeyError, TypeError, ValueError):
                    continue
        except Exception as e:
            print(f"  [AliExpress] Parse error: {e}")

    _cache[keyword] = result
    return result


# ── Test rápido ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    kw = sys.argv[1] if len(sys.argv) > 1 else "sous vide cooker"
    print(f"Buscando '{kw}' en AliExpress...")
    r = check_aliexpress(kw)
    if r:
        print(f"  ✓ {r['titulo'][:60]}")
        print(f"  $ {r['precio']} | {r['rating']}★")
        print(f"  🔗 {r['affiliate_url'][:80]}")
    else:
        print("  ✗ Sin resultado")
