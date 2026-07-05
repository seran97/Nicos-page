# -*- coding: utf-8 -*-
"""
amazon_checker.py — Fase 2: Validación Amazon
Primario: Rainforest API (rainforestapi.com). Si falla (402/cuota agotada/error),
cae a scraping directo de la página de búsqueda de Amazon.
Sweet spot: $15-$250, rating >= 4.0, reviews >= 50
"""

import os, re, time, random, requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

RAINFOREST_KEY = os.getenv("RAINFOREST_KEY")
AMAZON_TAG     = os.getenv("AMAZON_TAG", "trendvortex00-20")
AMAZON_DOMAIN  = os.getenv("AMAZON_DOMAIN", "amazon.com")  # amazon.es para España

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36",
]


def _scrape_amazon(keyword: str, precio_min: float, precio_max: float,
                    rating_min: float, reviews_min: int) -> dict | None:
    """
    Fallback sin API: scrapea la página de resultados de búsqueda de Amazon.
    Solo se usa cuando Rainforest no responde (cuota agotada, 402, error).
    """
    try:
        headers = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
        }
        url = f"https://www.{AMAZON_DOMAIN}/s"
        # Cookie i18n-prefs=USD fuerza precios en dólares aunque la IP sea de Colombia
        resp = requests.get(url, params={"k": keyword}, headers=headers,
                             cookies={"i18n-prefs": "USD"}, timeout=15)
        if resp.status_code != 200:
            print(f"  [Amazon-scrape] HTTP {resp.status_code} para '{keyword}'")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select('div[data-component-type="s-search-result"]')[:8]

        for card in cards:
            asin = card.get("data-asin", "")
            if not asin:
                continue

            titulo_el = card.select_one("h2 span")
            titulo = titulo_el.get_text(strip=True) if titulo_el else ""

            precio_el = card.select_one("span.a-price > span.a-offscreen")
            precio_texto = precio_el.get_text(strip=True) if precio_el else ""
            precio_match = re.search(r"[\d,.]+", precio_texto.replace(",", ""))
            precio = float(precio_match.group()) if precio_match else 0

            rating_row = card.select_one("div.a-row.a-size-small")
            rating = 0
            reviews = 0
            if rating_row:
                rating_link = rating_row.select_one("a[aria-label*='out of 5 stars']")
                if rating_link:
                    rating_match = re.search(r"([\d.]+) out of 5", rating_link.get("aria-label", ""))
                    rating = float(rating_match.group(1)) if rating_match else 0
                reviews_match = re.search(r"\(?([\d,]+)\)?$", rating_row.get_text(strip=True))
                if reviews_match:
                    reviews = int(reviews_match.group(1).replace(",", ""))

            img_el = card.select_one("img.s-image")
            imagen_url = img_el.get("src", "") if img_el else ""

            if not (precio_min <= precio <= precio_max):
                continue
            if rating < rating_min:
                continue
            if reviews < reviews_min:
                continue
            if not titulo:
                continue

            return {
                "asin":          asin,
                "titulo":        titulo[:120],
                "precio":        precio,
                "rating":        rating,
                "reviews":       reviews,
                "imagen_url":    imagen_url,
                "affiliate_url": f"https://www.{AMAZON_DOMAIN}/dp/{asin}?tag={AMAZON_TAG}",
            }

        print(f"  [Amazon-scrape] Ningún producto cumple filtros para '{keyword}'")
        return None

    except Exception as e:
        print(f"  [Amazon-scrape] Error '{keyword}': {e}")
        return None


def validar_amazon(keyword: str, precio_min=15, precio_max=250,
                   rating_min=4.0, reviews_min=50) -> dict | None:
    """
    Busca el mejor producto Amazon para el keyword dado.
    Intenta Rainforest API primero; si falla, cae a scraping directo.
    Retorna dict con datos del producto o None si no hay match.
    """
    if not RAINFOREST_KEY:
        print("  [Amazon] Sin RAINFOREST_KEY en .env — usando scraping directo")
        time.sleep(random.uniform(1, 3))
        return _scrape_amazon(keyword, precio_min, precio_max, rating_min, reviews_min)

    try:
        resp = requests.get(
            "https://api.rainforestapi.com/request",
            params={
                "api_key":       RAINFOREST_KEY,
                "type":          "search",
                "amazon_domain": AMAZON_DOMAIN,
                "search_term":   keyword,
                "sort_by":       "featured",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  [Amazon] HTTP {resp.status_code} para '{keyword}' — cae a scraping directo")
            time.sleep(random.uniform(1, 3))
            return _scrape_amazon(keyword, precio_min, precio_max, rating_min, reviews_min)

        resultados = resp.json().get("search_results", [])
        if not resultados:
            print(f"  [Amazon] Sin resultados para '{keyword}' — cae a scraping directo")
            time.sleep(random.uniform(1, 3))
            return _scrape_amazon(keyword, precio_min, precio_max, rating_min, reviews_min)

        for item in resultados[:8]:
            precio  = item.get("price", {}).get("value", 0) or 0
            rating  = item.get("rating", 0) or 0
            reviews = item.get("ratings_total", 0) or 0
            titulo  = item.get("title", "")
            asin    = item.get("asin", "")

            if not asin:
                continue
            if not (precio_min <= precio <= precio_max):
                continue
            if rating < rating_min:
                continue
            if reviews < reviews_min:
                continue

            return {
                "asin":          asin,
                "titulo":        titulo[:120],
                "precio":        precio,
                "rating":        rating,
                "reviews":       reviews,
                "imagen_url":    item.get("image", ""),
                "affiliate_url": f"https://www.{AMAZON_DOMAIN}/dp/{asin}?tag={AMAZON_TAG}",
            }

        print(f"  [Amazon] Ningún producto cumple filtros para '{keyword}' "
              f"(${precio_min}-${precio_max}, {rating_min}+★, {reviews_min}+ reviews)")
        return None

    except Exception as e:
        print(f"  [Amazon] Error '{keyword}': {e} — cae a scraping directo")
        time.sleep(random.uniform(1, 3))
        return _scrape_amazon(keyword, precio_min, precio_max, rating_min, reviews_min)


check_amazon = validar_amazon


if __name__ == "__main__":
    # Test rápido
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    kw = sys.argv[1] if len(sys.argv) > 1 else "sous vide cooker"
    print(f"Buscando en Amazon: '{kw}'")
    result = validar_amazon(kw)
    if result:
        print(f"  Titulo : {result['titulo']}")
        print(f"  Precio : ${result['precio']}")
        print(f"  Rating : {result['rating']} ({result['reviews']} reviews)")
        print(f"  Link   : {result['affiliate_url']}")
    else:
        print("  Sin producto valido")
