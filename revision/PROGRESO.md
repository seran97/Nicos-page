# Revisión de páginas de trendvortex.tech — progreso

Se trabaja **por partes**. Al terminar cada parte: marcarla aquí con fecha y commit, y hacer
`git commit` + `git push` de lo que toque `docs/`. Si una sesión se corta a mitad de una parte,
la siguiente sesión retoma leyendo este archivo y los JSON de estado de esa parte.

Mientras tanto siguen corriendo solos (no tocar): ciclo de redes (Instagram, Pinterest,
Telegram, Search Console ~10/día) en `DRIVE PERSONAL/Escritorio/Sergio- Personal/bot redes sociales/ciclo_redes.py`.

## Hecho
- [x] **Parte 1 · Limpieza** (2026-10-12, commit ae385c2): `noindex` a 267 páginas duplicadas/basura
      (`noindex_paginas.json`); sitemap y RSS las excluyen.
- [x] **Parte 2 · Requisitos y contenido** (2026-10-18, commit 3c359d0):
      36 guías nuevas (63 en total) y hubs con guías arriba; quitadas las experiencias en primera
      persona inventadas en ~350 páginas; canonicals de eBay; enlaces legales rotos; páginas
      contact.html y affiliate-disclosure.html; frase de Amazon Associates; portada sin noindex.

## Pendiente (en este orden)
- [ ] **Parte 3 · Páginas delgadas** — 20 páginas indexables con < 450 palabras
      (`revision/paginas_cortas.json`). Por cada una decidir: comparativas sin sentido
      (p. ej. "gaming-headset-vs-gaming-mouse") → `noindex`; reseñas válidas → enriquecer con una
      sección útil en voz neutra (sin primera persona, sin inventar datos). Lotes de 10 páginas;
      guardar en `revision/parte3_hecho.json` cada slug terminado.
- [ ] **Parte 4 · Títulos y descripciones** — ~250 títulos > 70 caracteres y ~60 descripciones
      fuera de 70–165. Solo con script (barato): quitar " — Expert Pick + Buying Guide" y similares;
      no tocar las 63 guías. Correr `python revision/auditar_paginas.py` antes y después.
- [ ] **Parte 5 · Medir indexación ~2026-10-25** — `python revision/medir_indexacion.py`
      (solo lectura, no gasta la cuota de "Solicitar indexación"). Comparar con
      `indexacion_2026-10-18.json`: 44/400 indexadas, 19 de 32 pedidas, hubs "Rastreada sin indexar".

## Herramientas
- `revision/auditar_paginas.py` — auditoría de requisitos (title, description, canonical, h1,
  JSON-LD, rel=sponsored, aviso afiliado, enlaces internos, palabras por tipo).
- `revision/medir_indexacion.py` — estado real en Google de todas las URLs del sitemap.
- `gsc_solicitar_indexacion.py` + `gsc_cola.json` — "Solicitar indexación" diario (lo corre el ciclo).
- `indexnow_enviar.py` — reenviar URLs a Bing/IndexNow tras cambios.
