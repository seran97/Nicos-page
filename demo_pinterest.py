# -*- coding: utf-8 -*-
"""
demo_pinterest.py — Script de demostración para el video de Pinterest
"Standard access". Usa el mismo código de producción (pinterest_poster.py)
que corre dentro del orquestador cuando se publica una página nueva.
"""
from pinterest_poster import create_pin

print("=" * 70)
print("TrendVortex Bot -- demo: publicar un Pin para una pagina nueva")
print("=" * 70)

page_url   = "https://trendvortex.tech/best-air-fryer"
image_url  = "https://m.media-amazon.com/images/I/81uj+Di8s7L._AC_UY218_.jpg"
title      = "Best Air Fryer 2026 -- Top Picks"
description = "Honest picks for the best air fryer, reviewed by TrendVortex."

print(f"\nPagina publicada en TrendVortex: {page_url}")
print("Generando Pin automaticamente...\n")

ok = create_pin(page_url=page_url, image_url=image_url, title=title, description=description)

print("\nResultado:", "Pin publicado correctamente" if ok else "Fallo al publicar")
