"""Pide "Solicitar indexación" en Search Console (interfaz web) para una lista de URLs.

Usa el Chrome del bot (puerto 9223, cuenta de Google con acceso a la propiedad
https://trendvortex.tech/). Google permite ~10 solicitudes por día y propiedad:
el script para solo cuando aparece el aviso de cuota y retoma al día siguiente.

Uso:  python gsc_solicitar_indexacion.py [max]     # toma las pendientes de gsc_cola.json
Estado en gsc_cola.json: {"pendientes": [...], "hechas": {url: fecha}, "errores": {url: msg}}
"""
import json
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

CARPETA = Path(__file__).resolve().parent
COLA = CARPETA / "gsc_cola.json"
PROPIEDAD = "https://trendvortex.tech/"
CDP = "http://127.0.0.1:9223"
CUOTA = re.compile(r"Cuota superada|superado tu cuota|quota exceeded", re.I)


def cargar():
    return json.loads(COLA.read_text(encoding="utf-8"))


def guardar(c):
    COLA.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")


def solicitar(pg, url):
    pg.goto("https://search.google.com/search-console?resource_id=" + urllib.parse.quote(PROPIEDAD, safe=""))
    pg.wait_for_timeout(5000)
    caja = pg.locator('input[aria-label^="Inspeccionar cualquier URL"]').first
    caja.click()
    caja.fill(url)
    pg.keyboard.press("Enter")
    boton = pg.get_by_text(re.compile(r"^\s*Solicitar indexación\s*$", re.I)).first
    boton.wait_for(state="visible", timeout=90000)
    pg.wait_for_timeout(2000)
    estado = pg.locator("body").inner_text()
    if "La URL está en Google" in estado:
        return "ya_indexada"
    boton.click()
    # Google hace una prueba en vivo (1-2 min) y luego muestra el resultado en un diálogo
    for _ in range(180):
        pg.wait_for_timeout(1000)
        dialogo = pg.locator('[role="dialog"], [role="alertdialog"]')
        texto = " ".join(dialogo.nth(i).inner_text() for i in range(dialogo.count()))
        if CUOTA.search(texto):
            return "cuota"
        if re.search(r"Se ha solicitado la indexación|Indexing requested", texto, re.I):
            try:  # cerrar el diálogo; si el botón cambia de nombre, basta con Escape
                dialogo.get_by_role("button").last.click(timeout=5000)
            except Exception:
                pg.keyboard.press("Escape")
            return "solicitada"
        if re.search(r"error|problema", texto, re.I) and "Probando" not in texto:
            return "error: " + texto[:150].replace("\n", " ")
    return "error: sin respuesta tras 3 min"


def main(maximo):
    cola = cargar()
    with sync_playwright() as p:
        ctx = p.chromium.connect_over_cdp(CDP).contexts[0]
        pg = ctx.new_page()
        pg.bring_to_front()
        try:
            for url in list(cola["pendientes"])[:maximo]:
                res = solicitar(pg, url)
                print(f"[{datetime.now():%H:%M}] {res}: {url}", flush=True)
                if res == "cuota":
                    break
                cola["pendientes"].remove(url)
                if res.startswith("error"):
                    cola["errores"][url] = res
                else:
                    cola["hechas"][url] = f"{datetime.now():%Y-%m-%d %H:%M} {res}"
                guardar(cola)
        finally:
            pg.close()
    print(f"Hechas: {len(cola['hechas'])} | pendientes: {len(cola['pendientes'])}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
