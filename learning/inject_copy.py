# -*- coding: utf-8 -*-
"""
learning/inject_copy.py — Reemplaza el texto generico de una pagina
fallback con copy original (generado por agentes Claude Code, sin tocar
la API de Anthropic del usuario), MANTENIENDO intacta la estructura
HTML/CSS, el schema.org, los links de afiliado, precio, imagen y rating
reales (esos NO se tocan, son datos verificados de producto).

Recibe un diccionario "copy" por pagina (ver CAMPOS abajo) y hace
sustituciones puntuales sobre el HTML fallback existente.

CAMPOS que debe traer `copy` (todos str, excepto listas indicadas):
  hero_sub      : parrafo del hero (reemplaza la mencion a r/macro_radar)
  method_note   : parrafo del "method-box"
  pros          : lista de 3 strings
  cons          : lista de 2 strings
  not_for       : parrafo "Who this is NOT for"
  table_lead    : parrafo antes de la tabla comparativa
  guide_lead    : parrafo antes de la guia de compra
  guide_steps   : lista de 3 dicts {"title": str, "body": str}
  faq           : lista de 5 dicts {"q": str, "a": str}
"""
from __future__ import annotations

import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "docs"


def _replace_between(html: str, start_marker: str, end_marker: str, new_text: str,
                      count: int = 1) -> str:
    pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
    replacement = start_marker + new_text + end_marker
    return re.sub(pattern, lambda m: replacement, html, count=count, flags=re.DOTALL)


def inject(slug: str, copy: dict) -> bool:
    path = DOCS_DIR / f"best-{slug}" / "index.html"
    if not path.exists():
        return False
    html = path.read_text(encoding="utf-8", errors="ignore")

    # 1. Hero subtitle
    html = re.sub(
        r'(<p class="hero-sub">).*?(</p>)',
        lambda m: m.group(1) + copy["hero_sub"] + m.group(2),
        html, count=1, flags=re.DOTALL,
    )

    # 2. Method box note (mantiene el <strong> tag, cambia el texto siguiente)
    html = re.sub(
        r'(<strong>📋 Our Methodology</strong>\s*).*?(\s*</div>)',
        lambda m: m.group(1) + copy["method_note"] + m.group(2),
        html, count=1, flags=re.DOTALL,
    )

    # 3. Pros (3 <li>)
    pros_html = "".join(f"<li>{p}</li>" for p in copy["pros"])
    html = re.sub(
        r'(<h3>✅ PROS</h3>\s*<ul>).*?(</ul>)',
        lambda m: m.group(1) + pros_html + m.group(2),
        html, count=1, flags=re.DOTALL,
    )

    # 4. Cons (2 <li>)
    cons_html = "".join(f"<li>{c}</li>" for c in copy["cons"])
    html = re.sub(
        r'(<h3>⚠️ CONS</h3>\s*<ul>).*?(</ul>)',
        lambda m: m.group(1) + cons_html + m.group(2),
        html, count=1, flags=re.DOTALL,
    )

    # 5. Who it's NOT for
    html = re.sub(
        r'(<strong>🚫 Who this is NOT for</strong>\s*).*?(\s*</div>)',
        lambda m: m.group(1) + copy["not_for"] + m.group(2),
        html, count=1, flags=re.DOTALL,
    )

    # 6. Table lead paragraph (elimina mencion falsa a r/macro_radar)
    html = re.sub(
        r'(<div class="sec-eyebrow">Does It Clear the Bar\?</div>\s*<h2>.*?</h2>\s*<p class="lead">).*?(</p>)',
        lambda m: m.group(1) + copy["table_lead"] + m.group(2),
        html, count=1, flags=re.DOTALL,
    )

    # 7. Guide lead paragraph
    html = re.sub(
        r'(<div class="sec-eyebrow">Buying Guide</div>\s*<h2>.*?</h2>\s*<p class="lead">).*?(</p>)',
        lambda m: m.group(1) + copy["guide_lead"] + m.group(2),
        html, count=1, flags=re.DOTALL,
    )

    # 8. Guide steps (3 steps, cada uno con <strong>title</strong> + body)
    steps_html = "".join(
        f'<div class="guide-step"><strong>{s["title"]}</strong>{s["body"]}</div>'
        for s in copy["guide_steps"]
    )
    html = re.sub(
        r'(<div class="guide-steps">).*?(</div>\s*</section>\s*<div class="divider"></div>\s*<!-- MID-PAGE CTA -->)',
        lambda m: m.group(1) + steps_html + m.group(2),
        html, count=1, flags=re.DOTALL,
    )

    # 9. FAQ (5 items) — reemplaza el bloque completo de 5 faq-item
    faq_html = "".join(
        f'<div class="faq-item"><div class="faq-q">{f["q"]}</div>'
        f'<div class="faq-a">{f["a"]}</div></div>'
        for f in copy["faq"]
    )
    html = re.sub(
        r'(<h2>Frequently Asked Questions</h2>\s*)(<div class="faq-item">.*?</div>\s*)(</section>)',
        lambda m: m.group(1) + faq_html + m.group(3),
        html, count=1, flags=re.DOTALL,
    )

    path.write_text(html, encoding="utf-8")
    return True
