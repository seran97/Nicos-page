# -*- coding: utf-8 -*-
"""
markets.py — Configuración de mercados globales TrendVortex

Cada mercado define:
  - amazon_domain : dominio de Amazon affiliate
  - ebay_site     : marketplace eBay
  - language      : idioma de las páginas generadas
  - currency      : moneda local
  - site_prefix   : subdirectorio en docs/ (ej: docs/es/, docs/uk/)
  - hreflang      : código para SEO internacional

Activa/desactiva mercados en ACTIVE_MARKETS.
"""
from __future__ import annotations

ALL_MARKETS: dict[str, dict] = {
    # ── Inglés ─────────────────────────────────────────────────────────────────
    "us": {
        "label":         "United States 🇺🇸",
        "amazon_domain": "amazon.com",
        "amazon_tag":    "",   # AMAZON_TAG del .env
        "ebay_site":     "EBAY-US",
        "language":      "en",
        "currency":      "USD",
        "currency_sym":  "$",
        "site_prefix":   "",            # raíz: docs/best-xxx/
        "hreflang":      "en-us",
        "price_min":     20,
        "price_max":     200,
    },
    "uk": {
        "label":         "United Kingdom 🇬🇧",
        "amazon_domain": "amazon.co.uk",
        "amazon_tag":    "",   # necesitas tag UK separado
        "ebay_site":     "EBAY-GB",
        "language":      "en",
        "currency":      "GBP",
        "currency_sym":  "£",
        "site_prefix":   "uk",         # docs/uk/best-xxx/
        "hreflang":      "en-gb",
        "price_min":     15,
        "price_max":     150,
    },
    "ca": {
        "label":         "Canada 🇨🇦",
        "amazon_domain": "amazon.ca",
        "amazon_tag":    "",
        "ebay_site":     "EBAY-US",    # eBay Canada usa el mismo que US
        "language":      "en",
        "currency":      "CAD",
        "currency_sym":  "C$",
        "site_prefix":   "ca",
        "hreflang":      "en-ca",
        "price_min":     25,
        "price_max":     250,
    },
    "au": {
        "label":         "Australia 🇦🇺",
        "amazon_domain": "amazon.com.au",
        "amazon_tag":    "",
        "ebay_site":     "EBAY-AU",
        "language":      "en",
        "currency":      "AUD",
        "currency_sym":  "A$",
        "site_prefix":   "au",
        "hreflang":      "en-au",
        "price_min":     30,
        "price_max":     280,
    },
    # ── Español ────────────────────────────────────────────────────────────────
    "es": {
        "label":         "España 🇪🇸",
        "amazon_domain": "amazon.es",
        "amazon_tag":    "",
        "ebay_site":     "EBAY-ES",
        "language":      "es",
        "currency":      "EUR",
        "currency_sym":  "€",
        "site_prefix":   "es",         # docs/es/best-xxx/
        "hreflang":      "es-es",
        "price_min":     20,
        "price_max":     180,
    },
    "mx": {
        "label":         "México 🇲🇽",
        "amazon_domain": "amazon.com.mx",
        "amazon_tag":    "",
        "ebay_site":     "EBAY-US",    # eBay MX usa US
        "language":      "es",
        "currency":      "MXN",
        "currency_sym":  "MX$",
        "site_prefix":   "mx",
        "hreflang":      "es-mx",
        "price_min":     300,
        "price_max":     3000,
    },
    "co": {
        "label":         "Colombia 🇨🇴",
        "amazon_domain": "amazon.com",   # Amazon no tiene .co — usa .com con envío
        "amazon_tag":    "",
        "ebay_site":     "EBAY-US",
        "language":      "es",
        "currency":      "COP",
        "currency_sym":  "COP$",
        "site_prefix":   "co",
        "hreflang":      "es-co",
        "price_min":     80000,
        "price_max":     700000,
    },
    # ── Alemán ─────────────────────────────────────────────────────────────────
    "de": {
        "label":         "Deutschland 🇩🇪",
        "amazon_domain": "amazon.de",
        "amazon_tag":    "",
        "ebay_site":     "EBAY-DE",
        "language":      "de",
        "currency":      "EUR",
        "currency_sym":  "€",
        "site_prefix":   "de",
        "hreflang":      "de-de",
        "price_min":     20,
        "price_max":     180,
    },
    # ── Francés ────────────────────────────────────────────────────────────────
    "fr": {
        "label":         "France 🇫🇷",
        "amazon_domain": "amazon.fr",
        "amazon_tag":    "",
        "ebay_site":     "EBAY-FR",
        "language":      "fr",
        "currency":      "EUR",
        "currency_sym":  "€",
        "site_prefix":   "fr",
        "hreflang":      "fr-fr",
        "price_min":     20,
        "price_max":     180,
    },
    # ── Italiano ───────────────────────────────────────────────────────────────
    "it": {
        "label":         "Italia 🇮🇹",
        "amazon_domain": "amazon.it",
        "amazon_tag":    "",
        "ebay_site":     "EBAY-IT",
        "language":      "it",
        "currency":      "EUR",
        "currency_sym":  "€",
        "site_prefix":   "it",
        "hreflang":      "it-it",
        "price_min":     20,
        "price_max":     180,
    },
    # ── Brasil ─────────────────────────────────────────────────────────────────
    "br": {
        "label":         "Brasil 🇧🇷",
        "amazon_domain": "amazon.com.br",
        "amazon_tag":    "",
        "ebay_site":     "EBAY-US",
        "language":      "pt",
        "currency":      "BRL",
        "currency_sym":  "R$",
        "site_prefix":   "br",
        "hreflang":      "pt-br",
        "price_min":     100,
        "price_max":     1000,
    },
}

# ── ACTIVA AQUÍ LOS MERCADOS QUE QUIERES ─────────────────────────────────────
# Empieza con US + ES (inglés y español cubren el 80% del tráfico)
# Activa más cuando tengas los affiliate tags de cada país
ACTIVE_MARKETS: list[str] = ["us", "es"]


def get_active() -> dict[str, dict]:
    return {k: ALL_MARKETS[k] for k in ACTIVE_MARKETS if k in ALL_MARKETS}


def get_market(code: str) -> dict | None:
    return ALL_MARKETS.get(code)


# ── Form interactivo para configurar mercados ─────────────────────────────────
def configure_markets():
    """Muestra un menú para activar/desactivar mercados."""
    print("\n" + "═"*55)
    print("  TrendVortex — Configuración de Mercados Globales")
    print("═"*55)

    current = set(ACTIVE_MARKETS)

    for code, mkt in ALL_MARKETS.items():
        status = "✓ ACTIVO " if code in current else "  inactivo"
        needs  = " ⚠ necesita affiliate tag" if not mkt["amazon_tag"] else ""
        print(f"  [{status}] {code.upper():4} {mkt['label']}{needs}")

    print("\n  Ingresa códigos para toggle (ej: uk,de,mx) o ENTER para confirmar:")
    entrada = input("  > ").strip().lower()

    if not entrada:
        print(f"  Mercados activos: {', '.join(ACTIVE_MARKETS)}")
        return

    cambios = [c.strip() for c in entrada.split(",") if c.strip()]
    for c in cambios:
        if c not in ALL_MARKETS:
            print(f"  ✗ '{c}' no reconocido — mercados válidos: {', '.join(ALL_MARKETS)}")
            continue
        if c in current:
            current.remove(c)
            print(f"  ✗ Desactivado: {ALL_MARKETS[c]['label']}")
        else:
            current.add(c)
            print(f"  ✓ Activado:    {ALL_MARKETS[c]['label']}")

    # Actualizar archivo
    new_list = [k for k in ALL_MARKETS if k in current]
    _update_active_markets(new_list)
    print(f"\n  Mercados activos: {', '.join(new_list)}")
    print("═"*55 + "\n")


def _update_active_markets(new_list: list[str]):
    """Reescribe ACTIVE_MARKETS en este mismo archivo."""
    import re
    from pathlib import Path
    path = Path(__file__)
    content = path.read_text(encoding="utf-8")
    new_line = f'ACTIVE_MARKETS: list[str] = {json_repr(new_list)}'
    content = re.sub(
        r'ACTIVE_MARKETS: list\[str\] = \[.*?\]',
        new_line,
        content,
        flags=re.DOTALL
    )
    path.write_text(content, encoding="utf-8")


def json_repr(lst: list) -> str:
    items = ', '.join(f'"{x}"' for x in lst)
    return f'[{items}]'


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    configure_markets()
