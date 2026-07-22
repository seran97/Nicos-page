# -*- coding: utf-8 -*-
"""
page_improver.py — Usa Claude (Anthropic) para reescribir una página ya
publicada que Google no ha indexado, reforzando las señales on-page que
más pesan para indexación (contenido único y más profundo, title/meta
distintivos, estructura semántica), sin tocar los links de afiliado ni el
disclosure legal.
"""
from __future__ import annotations
import os, re
from pathlib import Path

import anthropic

DOCS_DIR     = Path("docs")
CLAUDE_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


PROMPT = """Eres un editor SEO senior. La siguiente página HTML ya está publicada \
pero Google todavía no la ha indexado tras varios días. Reescríbela para \
maximizar las probabilidades de indexación, manteniendo el mismo producto/nicho.

Reglas estrictas:
- NO cambies ningún href, URL de afiliado, tag de tracking, ni el bloque de \
  disclosure legal — cópialos EXACTAMENTE igual.
- Reescribe el <title> y la meta description para que sean únicos y \
  específicos (evita frases genéricas tipo "Best X 2026 — Top Picks").
- Amplía el contenido real (texto, no relleno): agrega detalles concretos, \
  comparaciones, casos de uso, una sección FAQ más completa. Apunta a que el \
  contenido de texto visible sea sustancialmente más largo y único que el actual.
- Conserva la estructura HTML/CSS existente (misma clase de body, mismos \
  estilos) — solo enriquece el contenido dentro de las secciones.
- Devuelve el documento HTML COMPLETO (desde <!DOCTYPE> o <html> hasta \
  </html>), sin explicaciones ni markdown, listo para guardarse tal cual.

HTML actual:
{html}
"""


def improve_page(slug: str) -> bool:
    """
    Reescribe docs/{slug}/index.html vía Claude. Retorna True si se mejoró
    y se sobreescribió el archivo, False si no había cliente/página o falló.
    """
    client = _get_client()
    if client is None:
        print("  [IMPROVER] Sin ANTHROPIC_API_KEY — saltando mejora")
        return False

    page_path = DOCS_DIR / slug / "index.html"
    if not page_path.exists():
        print(f"  [IMPROVER] {page_path} no existe — saltando")
        return False

    current_html = page_path.read_text(encoding="utf-8")

    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8000,
            messages=[{"role": "user", "content": PROMPT.format(html=current_html)}],
        )
        new_html = resp.content[0].text.strip()
    except Exception as e:
        print(f"  [IMPROVER] ERROR Claude para {slug}: {e}")
        return False

    # Sanidad mínima: que siga siendo un documento HTML completo
    if "<html" not in new_html.lower() or "</html>" not in new_html.lower():
        print(f"  [IMPROVER] Respuesta de Claude no parece HTML válido para {slug} — descartada")
        return False

    # Nunca perder los links de afiliado si Claude se los comió por error
    orig_links = set(re.findall(r'href="([^"]+)"', current_html))
    new_links  = set(re.findall(r'href="([^"]+)"', new_html))
    affiliate_orig = {l for l in orig_links if "tag=" in l or "affiliate" in l or "partner" in l}
    if affiliate_orig and not affiliate_orig.issubset(new_links):
        print(f"  [IMPROVER] Claude alteró los links de afiliado en {slug} — descartada")
        return False

    page_path.write_text(new_html, encoding="utf-8")
    print(f"  [IMPROVER] {slug} reescrita ({len(new_html)} bytes)")
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for s in sys.argv[1:]:
            improve_page(s)
    else:
        print("Uso: python page_improver.py <slug1> [slug2 ...]")
