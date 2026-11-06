# -*- coding: utf-8 -*-
"""fix_ebay_links.py — Replaces dead rover.ebay.com affiliate links with current EPN links.

rover.ebay.com/rover/1/... no longer redirects: it answers with a 1x1 GIF, so every
eBay click on the site ended on a blank page and EPN recorded 0 clicks.

- Live listing      -> https://www.ebay.com/itm/<id>?<EPN params>
- Ended / not found -> eBay search for the page's product, same EPN params
Touches docs/*/index.html and the affiliate_url fields of the manifests.

Usage:  python fix_ebay_links.py [--dry]
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus, unquote

import requests

from ebay_checker import EBAY_SID, _get_oauth_token, epn_link

sys.stdout.reconfigure(encoding="utf-8")
DOCS = Path("docs")
MANIFESTS = ["regen_manifest.json", "regen_manifest_125.json", "regen_manifest_todo.json"]
ROVER = re.compile(r"https://rover\.ebay\.com/rover/1/[^\"' <]*")
_estado: dict[str, bool] = {}


def vivo(item_id: str, token: str) -> bool:
    """True if the listing is still buyable (multi-variation listings answer 400 but are live)."""
    if item_id not in _estado:
        r = requests.get("https://api.ebay.com/buy/browse/v1/item/get_item_by_legacy_id",
                         params={"legacy_item_id": item_id}, timeout=20,
                         headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"})
        if r.status_code == 400 and "item_group" in r.text:
            _estado[item_id] = True
        elif r.status_code == 200:
            disp = r.json().get("estimatedAvailabilities", [{}])[0]
            _estado[item_id] = disp.get("estimatedAvailabilityStatus", "IN_STOCK") != "OUT_OF_STOCK"
        else:
            _estado[item_id] = False
    return _estado[item_id]


def busqueda(slug: str) -> str:
    palabras = re.sub(r"^best-|-(ebay|aliexpress)$", "", slug).replace("-", " ")
    return f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(palabras)}"


def nuevo(rover: str, slug: str, token: str) -> str:
    destino = unquote(rover.replace("&amp;", "&").split("mpre=", 1)[-1])
    m = re.search(r"/itm/(\d+)", destino)
    if m and vivo(m.group(1), token):
        return epn_link(f"https://www.ebay.com/itm/{m.group(1)}")
    return epn_link(busqueda(slug))


def main(dry=False):
    token = _get_oauth_token()
    if not (token and EBAY_SID):
        sys.exit("Faltan credenciales de eBay en .env")
    paginas = cambios = 0
    for html in sorted(DOCS.glob("*/index.html")):
        texto = html.read_text(encoding="utf-8")
        if "rover.ebay.com" not in texto:
            continue
        slug = html.parent.name
        enlaces = {r: nuevo(r, slug, token) for r in set(ROVER.findall(texto))}
        for viejo, url in enlaces.items():
            # inside HTML attributes the & must stay escaped
            texto = texto.replace(viejo, url.replace("&", "&amp;") if "&amp;" in viejo else url)
        cambios += len(enlaces)
        paginas += 1
        if not dry:
            html.write_text(texto, encoding="utf-8")
    for nombre in MANIFESTS:
        ruta = Path(nombre)
        if not ruta.exists():
            continue
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        n = 0
        for m in datos:
            if "rover.ebay.com" in m.get("affiliate_url", ""):
                m["affiliate_url"] = nuevo(m["affiliate_url"], m.get("slug", ""), token)
                n += 1
        if n and not dry:
            ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {nombre}: {n} enlaces")
    vivos = sum(_estado.values())
    print(f"{'(simulación) ' if dry else ''}{paginas} páginas, {cambios} enlaces distintos; "
          f"artículos activos {vivos}, terminados {len(_estado) - vivos} -> búsqueda")


if __name__ == "__main__":
    main("--dry" in sys.argv)
