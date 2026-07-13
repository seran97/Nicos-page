# -*- coding: utf-8 -*-
"""
pipeline.py — Orquestador completo
Flujo: Reddit → Trends → Amazon → HTML → Git deploy

Uso:
  python pipeline.py              # procesa leads.csv existentes
  python pipeline.py --watch      # loop: radar + pipeline cada 3h
  python pipeline.py --batch N    # genera páginas de los N mejores leads del CSV
  python pipeline.py --deploy     # solo hace git push de docs/ existentes
"""

import sys, os, csv, time, subprocess
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

LEADS_FILE  = Path("leads.csv")
DOCS_DIR    = Path("docs")
GITHUB_USER = os.getenv("GITHUB_USER", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "niche-pages")
SITE_URL    = os.getenv("SITE_URL", "https://tu-dominio.com")


# ══════════════════════════════════════════════════════════════════════════════
# GIT DEPLOY
# ══════════════════════════════════════════════════════════════════════════════
def deploy_github(slugs: list[str]) -> bool:
    """Hace commit y push de las páginas nuevas. ~15 segundos."""
    if not slugs:
        return True
    try:
        paths = [f"docs/best-{s}/" for s in slugs] + ["docs/sitemap.xml", "docs/index.html"]
        subprocess.run(["git", "add"] + paths, check=True)
        msg = f"add: {', '.join(slugs[:3])}{'...' if len(slugs) > 3 else ''}"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        subprocess.run(["git", "push"], check=True)
        base = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}" if GITHUB_USER else SITE_URL
        print(f"  [Deploy] Live en {base}/best-{slugs[0]}/")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [Deploy] Error git: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# PROCESAR UN LEAD → página completa
# ══════════════════════════════════════════════════════════════════════════════
def procesar_lead(row: dict) -> str | None:
    """
    Toma una fila del leads.csv, valida Amazon y genera la página HTML.
    Retorna el slug creado o None si falla.
    """
    from amazon_checker import validar_amazon
    from page_generator import generar_pagina, actualizar_sitemap, actualizar_index_html

    keyword    = row.get("keyword", "").strip()
    subreddit  = row.get("subreddit", "")
    amazon_cat = row.get("amazon_cat", "")

    if not keyword:
        return None

    # Reconstruir dict trends desde el CSV
    trends = {
        "hits_max":      float(row.get("hits_max", 0) or 0),
        "hits_reciente": float(row.get("hits_reciente", 0) or 0),
        "slope":         float(row.get("slope", 0) or 0),
        "trending":      row.get("trending", "False") == "True",
    }

    print(f"\n  [{amazon_cat}] '{keyword}'")

    amazon = validar_amazon(keyword)
    if amazon is None:
        print(f"  [skip] Sin producto Amazon valido para '{keyword}'")
        return None

    print(f"  [Amazon] ${amazon['precio']} | {amazon['rating']}★ | "
          f"{amazon['reviews']:,} reviews")

    slug_creado = generar_pagina(keyword, amazon, trends, subreddit, amazon_cat)
    actualizar_sitemap()
    actualizar_index_html()
    return slug_creado


# ══════════════════════════════════════════════════════════════════════════════
# LEER LEADS CSV
# ══════════════════════════════════════════════════════════════════════════════
def cargar_leads(max_rows: int = 0) -> list[dict]:
    if not LEADS_FILE.exists():
        print(f"  [WARN] No existe {LEADS_FILE}. Corre primero radar_nichos.py")
        return []
    with LEADS_FILE.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Ordenar por comisión desc, luego slope desc
    rows.sort(key=lambda r: (
        -float(r.get("comision_pct", 0) or 0),
        -float(r.get("slope", 0) or 0)
    ))
    return rows[:max_rows] if max_rows else rows


# ══════════════════════════════════════════════════════════════════════════════
# MODO BATCH — genera N páginas de los mejores leads
# ══════════════════════════════════════════════════════════════════════════════
def modo_batch(n: int = 10):
    print(f"\n{'='*55}")
    print(f"  BATCH — generando páginas de los {n} mejores leads")
    print(f"{'='*55}")

    leads = cargar_leads(max_rows=n)
    if not leads:
        return

    slugs_creados = []
    for i, row in enumerate(leads, 1):
        print(f"\n  [{i}/{len(leads)}]")
        slug = procesar_lead(row)
        if slug:
            slugs_creados.append(slug)
        time.sleep(2)

    print(f"\n  {len(slugs_creados)} páginas generadas")

    if slugs_creados and GITHUB_USER:
        print("\n  Subiendo a GitHub Pages...")
        deploy_github(slugs_creados)


# ══════════════════════════════════════════════════════════════════════════════
# MODO WATCH — radar + pipeline en loop
# ══════════════════════════════════════════════════════════════════════════════
def modo_watch():
    import importlib, radar_nichos
    print("  Modo watch — radar + pipeline cada 3h\n")
    ciclo = 1
    while True:
        print(f"\n{'='*55}  CICLO #{ciclo}  {'='*55}")

        # Fase 1: detectar nichos
        radar_nichos.run_ciclo(ciclo)

        # Fase 2+3: procesar leads nuevos
        leads = cargar_leads()
        slugs = []
        for row in leads[-5:]:  # últimos 5 leads del ciclo
            slug = procesar_lead(row)
            if slug:
                slugs.append(slug)
            time.sleep(2)

        if slugs and GITHUB_USER:
            deploy_github(slugs)

        print(f"\n  Próximo ciclo en 3h...")
        time.sleep(3 * 3600)
        ciclo += 1


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    args = sys.argv[1:]

    print("Pipeline — Radar de Nichos")
    print(f"  SITE_URL    : {SITE_URL}")
    print(f"  GitHub      : {GITHUB_USER}/{GITHUB_REPO}" if GITHUB_USER else "  GitHub      : no configurado")
    print()

    if "--deploy" in args:
        # Solo deploy de lo que ya existe en docs/
        from page_generator import actualizar_sitemap, actualizar_index_html
        actualizar_sitemap()
        actualizar_index_html()
        slugs = [p.parent.name.replace("best-", "")
                 for p in sorted(DOCS_DIR.glob("*/index.html"))
                 if p.parent != DOCS_DIR]
        deploy_github(slugs)

    elif "--watch" in args:
        modo_watch()

    elif "--batch" in args:
        idx = args.index("--batch")
        n = int(args[idx + 1]) if idx + 1 < len(args) else 10
        modo_batch(n)

    else:
        # Por defecto: procesar todos los leads pendientes
        modo_batch(n=20)
