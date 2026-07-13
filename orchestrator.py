# -*- coding: utf-8 -*-
"""
orchestrator.py — TrendVortex Swarm Orchestrator
Mesa de vendedores + diseñadores + analistas (patrón SwardRisk).

Flujo por lead:
  1. TrendAgent   — valida si el nicho tiene momentum (ML score ≥ 45)
  2. AmazonAgent  — valida producto ($30-$150, 4★+)  [via amazon_checker.py]
  3. SEOAgent     — genera title/meta/FAQs con Gemini Flash
  4. DesignerAgent— genera HTML rico con Claude API
  5. Deploy       — git push a GitHub Pages

Uso:
  python orchestrator.py                  # procesa leads del CSV, despliega todo
  python orchestrator.py --dry-run        # sin deploy
  python orchestrator.py --limit 5        # procesa 5 leads máximo
  python orchestrator.py --watch          # loop continuo (cada 6h)
"""
from __future__ import annotations
import os, sys, time, subprocess, argparse, collections
from pathlib import Path
from datetime import datetime

# Cargar .env antes de importar agentes
from dotenv import load_dotenv
load_dotenv()

import pandas as pd

from agents.base   import AgentType
from agents.trend_agent    import TrendAgent
from agents.seo_agent      import SEOAgent
from agents.designer_agent import DesignerAgent
from memory.swarm_memory   import SwarmMemory, Episode
from markets import get_active, ALL_MARKETS
from learning.niche_learner import NicheLearner

# ── Config ────────────────────────────────────────────────────────────────────
LEADS_CSV     = Path("leads.csv")          # output de radar_nichos.py
DOCS_DIR      = Path("docs")
GITHUB_USER   = os.getenv("GITHUB_USER",   "seran97")
GITHUB_REPO   = os.getenv("GITHUB_REPO",   "Nicos-page")
SITE_URL      = os.getenv("SITE_URL",      "https://trendvortex.tech")
WATCH_INTERVAL = 6 * 3600  # 6 horas en modo watch

# ── Rate limits (desde .env) ──────────────────────────────────────────────────
MAX_PAGES_PER_RUN       = int(os.getenv("MAX_PAGES_PER_RUN", "20"))
LEAD_SLEEP_SECONDS      = int(os.getenv("LEAD_SLEEP_SECONDS", "3"))
MAX_CLAUDE_CALLS_PER_HOUR = int(os.getenv("MAX_CLAUDE_CALLS_PER_HOUR", "40"))

# Contador de llamadas Claude en ventana deslizante de 1 hora
_claude_calls: collections.deque = collections.deque(maxlen=MAX_CLAUDE_CALLS_PER_HOUR + 10)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _claude_rate_limited() -> bool:
    """Revisa si ya alcanzamos el límite de llamadas Claude en la última hora."""
    now = time.time()
    # Limpiar llamadas viejas (> 1 hora)
    while _claude_calls and _claude_calls[0] < now - 3600:
        _claude_calls.popleft()
    if len(_claude_calls) >= MAX_CLAUDE_CALLS_PER_HOUR:
        oldest = _claude_calls[0]
        wait_s = int(3600 - (now - oldest)) + 5
        log(f"Rate limit Claude: {len(_claude_calls)}/{MAX_CLAUDE_CALLS_PER_HOUR} llamadas/hora. "
            f"Esperando {wait_s//60}m {wait_s%60}s", "⏳")
        time.sleep(wait_s)
        return False  # después de esperar, continuar
    return False


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str, icon: str = "·"):
    print(f"  {icon} [{ts()}] {msg}", flush=True)


def deploy_github(slugs: list[str], dry_run: bool = False):
    if not slugs or dry_run:
        return
    try:
        n = len(slugs)
        subprocess.run(["git", "add", "-f", "docs/"], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"[TrendVortex] +{n} pages auto-generated"],
            check=True
        )
        subprocess.run(["git", "push"], check=True)
        log(f"GitHub Pages actualizado: {n} página(s) desplegada(s)", "🚀")
    except subprocess.CalledProcessError as e:
        log(f"Error git: {e}", "✗")


def load_leads() -> pd.DataFrame | None:
    if not LEADS_CSV.exists():
        log("leads.csv no encontrado — corre radar_nichos.py primero", "✗")
        return None
    df = pd.read_csv(LEADS_CSV)
    required = {"keyword", "hits_reciente", "slope", "url"}
    missing  = required - set(df.columns)
    if missing:
        log(f"leads.csv le faltan columnas: {missing}", "✗")
        return None
    # Ordenar: comisión desc, slope desc
    if "comision_pct" in df.columns:
        df = df.sort_values(["comision_pct", "slope"], ascending=False)
    return df.reset_index(drop=True)


# ── Agentes singleton ─────────────────────────────────────────────────────────

def build_agents():
    log("Inicializando agentes...", "⚙")
    return {
        "trend":    TrendAgent(),
        "seo":      SEOAgent(),
        "designer": DesignerAgent(),
    }


# ── Pipeline por lead ─────────────────────────────────────────────────────────

def process_lead(row: pd.Series, agents: dict, memory: SwarmMemory,
                 dry_run: bool = False, learner: NicheLearner | None = None) -> str | None:
    """
    Ejecuta el pipeline completo para un lead.
    Retorna el slug desplegado, o None si se descartó.
    """
    keyword   = str(row.get("keyword", "")).strip()
    subreddit = str(row.get("subreddit", ""))
    amazon_cat= str(row.get("amazon_cat", "General"))
    commission= float(row.get("comision_pct", 3.0))

    if not keyword:
        return None

    # ── Skip si ya fue procesado ──────────────────────────────────────────────
    if memory.keyword_already_processed(keyword):
        log(f"Skip '{keyword}' — ya en memoria", "⏭")
        return None

    print(f"\n{'─'*55}")
    log(f"Procesando: '{keyword}' | r/{subreddit} | {amazon_cat} {commission}%", "🔎")

    # ── 1. TrendAgent ─────────────────────────────────────────────────────────
    # Construir serie temporal desde el CSV (usa hits_reciente y slope como proxy)
    hits_rec = float(row.get("hits_reciente", 0))
    slope    = float(row.get("slope", 0))
    # Simular 16-semana series desde el slope (sin llamada a pytrends)
    import numpy as np
    base = max(0, hits_rec - slope * 8)
    series = [max(0, base + slope * i + np.random.normal(0, 2)) for i in range(16)]
    series[-1] = hits_rec  # anclar al dato real

    trend_ctx = {
        "keyword": keyword,
        "pytrends_series": series,
        "reddit_posts": int(row.get("hits_max", 1)),
        "subreddit": subreddit,
        "amazon_commission": commission,
    }
    trend_result = agents["trend"].act(trend_ctx)
    log(f"TrendAgent → {trend_result.reasoning}", "📈" if trend_result.success else "↘")

    memory.add(Episode(
        timestamp=datetime.now().isoformat(),
        agent_type=AgentType.TREND_ANALYST.value,
        keyword=keyword,
        action="VALIDATED" if trend_result.success else "SKIPPED",
        score=trend_result.payload.get("composite_score", 0),
        reasoning=trend_result.reasoning,
        payload=trend_result.payload,
    ))

    if not trend_result.success:
        log(f"'{keyword}' descartado por TrendAgent", "✗")
        return None

    # ── 2. Multi-source product validator (Amazon → eBay, por mercado) ──────
    active_markets = get_active()
    market_code    = str(row.get("market", "us"))
    market         = active_markets.get(market_code, active_markets.get("us"))

    try:
        from ebay_checker import check_product
        # Pasar el dominio Amazon del mercado activo
        os.environ["AMAZON_DOMAIN"] = market["amazon_domain"]
        if market.get("amazon_tag"):
            os.environ["AMAZON_TAG"] = market["amazon_tag"]
        amazon = check_product(keyword)
    except Exception as e:
        log(f"Product checker error: {e}", "✗")
        amazon = None

    if not amazon:
        log(f"Sin producto para '{keyword}' en {market['label']}", "✗")
        memory.add(Episode(
            timestamp=datetime.now().isoformat(),
            agent_type=AgentType.AMAZON_VALIDATOR.value,
            keyword=keyword, action="SKIPPED", score=0,
            reasoning=f"Sin producto en {market['amazon_domain']}",
        ))
        return None

    source = amazon.get("source", "amazon").upper()
    sym    = market["currency_sym"]
    log(f"{source} [{market['label']}] → {amazon['titulo'][:44]}… {sym}{amazon['precio']:.2f} {amazon['rating']}★", "🛒")

    slugs = []
    main_slug = _seo_and_design(
        keyword, amazon, trend_result, subreddit, amazon_cat, market,
        agents, memory, dry_run, learner,
    )
    if main_slug:
        slugs.append(main_slug)

    # ── eBay en paralelo (no solo fallback) ──────────────────────────────────
    # Si Amazon fue la fuente principal, generamos TAMBIÉN una página eBay
    # para el mismo keyword, así eBay no se queda solo esperando que Amazon falle.
    if amazon.get("source") == "amazon":
        try:
            from ebay_checker import check_ebay
            ebay = check_ebay(keyword)
        except Exception as e:
            log(f"eBay checker error: {e}", "✗")
            ebay = None

        if ebay:
            ebay["source"] = "ebay"
            log(f"EBAY [{market['label']}] → {ebay['titulo'][:44]}… {sym}{ebay['precio']:.2f} {ebay['rating']}★", "🛍")
            ebay_slug = _seo_and_design(
                keyword, ebay, trend_result, subreddit, amazon_cat, market,
                agents, memory, dry_run, learner,
            )
            if ebay_slug:
                slugs.append(ebay_slug)

        # ── AliExpress en paralelo (mismo patrón que eBay) ───────────────────
        try:
            from aliexpress_checker import check_aliexpress
            aliexpress = check_aliexpress(keyword)
        except Exception as e:
            log(f"AliExpress checker error: {e}", "✗")
            aliexpress = None

        if aliexpress:
            aliexpress["source"] = "aliexpress"
            log(f"ALIEXPRESS [{market['label']}] → {aliexpress['titulo'][:44]}… {sym}{aliexpress['precio']:.2f} {aliexpress['rating']}★", "🧧")
            ali_slug = _seo_and_design(
                keyword, aliexpress, trend_result, subreddit, amazon_cat, market,
                agents, memory, dry_run, learner,
            )
            if ali_slug:
                slugs.append(ali_slug)

    return slugs if slugs else None


def _seo_and_design(keyword, product, trend_result, subreddit, amazon_cat,
                     market, agents, memory, dry_run,
                     learner: NicheLearner | None = None) -> str | None:
    """Corre SEOAgent + DesignerAgent para un producto (Amazon o eBay) y
    retorna el slug desplegado, o None si se saltó."""

    # ── 3. SEO Agent ──────────────────────────────────────────────────────────
    seo_ctx = {
        "keyword": keyword,
        "amazon":  product,
        "amazon_cat": amazon_cat,
        "trend_payload": trend_result.payload,
        "subreddit": subreddit,
        "language": market["language"],
    }
    seo_result = agents["seo"].act(seo_ctx)
    log(f"SEOAgent → {seo_result.reasoning}", "🔑")

    # ── 4. Designer Agent (Claude API) — con rate limit ─────────────────────
    if not dry_run and not _claude_rate_limited():
        design_ctx = {
            "keyword":      keyword,
            "amazon":       product,
            "trend_payload":trend_result.payload,
            "subreddit":    subreddit,
            "amazon_cat":   amazon_cat,
            "seo_content":  seo_result.payload,
            "market":       market,
        }
        _claude_calls.append(time.time())
        design_result = agents["designer"].act(design_ctx)
        log(f"Designer → {design_result.reasoning}", "🎨")

        slug     = design_result.payload.get("slug", "")
        url      = design_result.payload.get("url", "")
        fallback = design_result.payload.get("fallback", False)

        memory.add(Episode(
            timestamp=datetime.now().isoformat(),
            agent_type=AgentType.DESIGNER.value,
            keyword=keyword, action="DESIGNED",
            score=trend_result.payload.get("composite_score", 0),
            reasoning=design_result.reasoning,
            payload={"slug": slug, "url": url, "fallback": fallback},
        ))

        if learner:
            learner.log(
                keyword=keyword, amazon_cat=amazon_cat,
                market=market.get("label", ""), source=product.get("source", "amazon"),
                action="DEPLOYED", fallback=fallback,
                score=trend_result.payload.get("composite_score", 0), slug=slug,
            )

        if fallback:
            log(f"Página lista (⚠ fallback, sin Claude) → {url}", "✓")
        else:
            log(f"Página lista → {url}", "✓")
        return slug
    else:
        log("Dry-run: saltar generación HTML", "⏭")
        return None


# ── Runner principal ──────────────────────────────────────────────────────────

def run_once(limit: int = 0, dry_run: bool = False, markets_override: list[str] | None = None):
    df = load_leads()
    if df is None:
        return

    # Mercados a procesar
    from markets import ACTIVE_MARKETS
    market_codes = markets_override or ACTIVE_MARKETS
    active       = {k: ALL_MARKETS[k] for k in market_codes if k in ALL_MARKETS}

    memory = SwarmMemory()
    agents = build_agents()
    learner = NicheLearner()

    # Aprendizaje: reordena por score y descarta duplicados semánticos /
    # sobre-concentración de categoría ANTES de recortar por el cap de la corrida.
    df = learner.rank_and_filter_leads(df)

    cap   = MAX_PAGES_PER_RUN if MAX_PAGES_PER_RUN > 0 else len(df)
    total = min(cap, len(df)) if not limit else min(limit, len(df), cap)

    print(f"\n{'═'*55}")
    print(f"  TrendVortex Swarm — {total} leads × {len(active)} mercados")
    print(f"  Mercados: {' · '.join(m['label'] for m in active.values())}")
    summary = memory.round_summary()
    print(f"  Memoria: {summary['total_episodes']} eps | {summary['deployed']} páginas")
    print(f"  Learner: {learner.summary().splitlines()[0]}")
    print(f"{'═'*55}")

    all_deployed: list[str] = []
    skipped = 0

    for market_code, market in active.items():
        print(f"\n  ── Mercado: {market['label']} ──")

        # Añadir columna market al df para este loop
        df_market = df.head(total).copy()
        df_market["market"] = market_code

        deployed_this = []
        for _, row in df_market.iterrows():
            page_slugs = process_lead(row, agents, memory, dry_run=dry_run, learner=learner)
            if page_slugs:
                for slug in page_slugs:
                    # Prefijo de mercado en el path (ej: "es/best-xxx")
                    full_slug = f"{market['site_prefix']}/{slug}" if market["site_prefix"] else slug
                    deployed_this.append(full_slug)
            else:
                skipped += 1
            time.sleep(LEAD_SLEEP_SECONDS)

        all_deployed.extend(deployed_this)

    # ── Deploy ────────────────────────────────────────────────────────────────
    if all_deployed and not dry_run:
        deploy_github(all_deployed, dry_run=dry_run)
        for full_slug in all_deployed:
            keyword = full_slug.split("/")[-1].replace("-", " ")
            memory.add(Episode(
                timestamp=datetime.now().isoformat(),
                agent_type=AgentType.DEPLOY.value,
                keyword=keyword, action="DEPLOYED", score=80,
                reasoning=f"{SITE_URL}/{full_slug}/",
                payload={"slug": full_slug},
            ))

    # ── Resumen final ─────────────────────────────────────────────────────────
    print(f"\n{'═'*55}")
    print(f"  RESUMEN GLOBAL")
    print(f"  ✓ Páginas desplegadas : {len(all_deployed)}")
    print(f"  ✗ Leads descartados   : {skipped}")
    print(f"  Mercados procesados   : {', '.join(active)}")
    if all_deployed:
        print(f"  URLs:")
        for s in all_deployed[:10]:
            print(f"    → {SITE_URL}/{s}/")
        if len(all_deployed) > 10:
            print(f"    ... y {len(all_deployed)-10} más")
    final = memory.round_summary()
    print(f"  Momentum del swarm    : {final['momentum_score']:.1f}/100")
    print(f"{'═'*55}\n")


def run_watch(limit_per_run: int = 10, markets_override: list[str] | None = None):
    while True:
        run_once(limit=limit_per_run, markets_override=markets_override)
        log(f"Próxima ejecución en {WATCH_INTERVAL//3600}h", "💤")
        time.sleep(WATCH_INTERVAL)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="TrendVortex Swarm Orchestrator")
    parser.add_argument("--limit",    type=int, default=0,   help="Límite de leads por corrida")
    parser.add_argument("--dry-run",  action="store_true",   help="Sin deploy ni páginas reales")
    parser.add_argument("--watch",    action="store_true",   help="Loop continuo cada 6h")
    parser.add_argument("--markets",  type=str, default="",  help="Mercados: us,es,uk,de,mx,...")
    parser.add_argument("--config-markets", action="store_true", help="Abrir menú de mercados")
    args = parser.parse_args()

    if args.config_markets:
        from markets import configure_markets
        configure_markets()
        sys.exit(0)

    markets_list = [m.strip() for m in args.markets.split(",") if m.strip()] or None

    if args.watch:
        run_watch(limit_per_run=args.limit or 10, markets_override=markets_list)
    else:
        run_once(limit=args.limit, dry_run=args.dry_run, markets_override=markets_list)
