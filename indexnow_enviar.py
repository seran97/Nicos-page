"""Envía las URLs del sitemap (sin las noindex) a IndexNow: Bing, Yandex, Seznam, Naver.

Google NO usa IndexNow; esto es para Bing y compañía. La clave está publicada en
docs/<clave>.txt (debe seguir en el sitio para que el envío valga).

Uso:  python indexnow_enviar.py            # todas las URLs del sitemap
      python indexnow_enviar.py URL [URL…]  # solo esas
"""
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CLAVE = "23251cf4998b4fc0b6ad261e5596e4a6"
HOST = "trendvortex.tech"
SITEMAP = Path(__file__).resolve().parent / "docs" / "sitemap.xml"


def enviar(urls):
    cuerpo = json.dumps({"host": HOST, "key": CLAVE, "keyLocation": f"https://{HOST}/{CLAVE}.txt",
                         "urlList": urls}).encode()
    for ep in ("https://www.bing.com/indexnow", "https://api.indexnow.org/indexnow"):
        req = urllib.request.Request(ep, data=cuerpo, headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            print(ep, urllib.request.urlopen(req, timeout=30).status, f"({len(urls)} URLs)")
        except urllib.error.HTTPError as e:
            print(ep, e.code, e.read()[:200].decode(errors="replace"))


if __name__ == "__main__":
    urls = sys.argv[1:] or re.findall(r"<loc>([^<]+)</loc>", SITEMAP.read_text(encoding="utf-8"))
    enviar(urls)
