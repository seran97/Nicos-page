# -*- coding: utf-8 -*-
"""
main.py — TrendVortex: Loop completo autónomo

Ciclo infinito:
  1. radar_nichos  → escanea Reddit + valida Trends → leads.csv
  2. orchestrator  → Trend ML → Amazon/eBay → SEO → Claude HTML → GitHub Pages
  3. Telegram      → alerta por cada página + resumen + heartbeat + informe diario
  4. Dormir N horas → repetir

Comandos:
  python main.py
  python main.py --limit 5
  python main.py --markets us,es
  python main.py --once
"""
from __future__ import annotations
import os, sys, time, argparse, threading
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

import requests

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SITE_URL         = os.getenv("SITE_URL", "https://trendvortex.tech")

RADAR_INTERVALO_H   = 3
SWARM_CADA_N_CICLOS = 1    # enjambre CADA ciclo (antes era cada 2)
HEARTBEAT_MIN       = 30   # ping de vida cada 30 min
INFORME_DIARIO_H    = 24   # informe diario cada 24h
MACRO_CADA_N_CICLOS = 4    # macro radar cada 4 ciclos (~12h)

# ── Estado global ─────────────────────────────────────────────────────────────
_ciclo_actual   = 0
_paginas_hoy:   list[str] = []
_inicio_sesion  = datetime.now()

# ── Telegram ──────────────────────────────────────────────────────────────────

def telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


# ── Heartbeat (hilo separado) ─────────────────────────────────────────────────

def _count_live_pages() -> int:
    """Cuenta páginas HTML en docs/ (excluye index.html raíz)."""
    docs = Path(__file__).parent / "docs"
    if not docs.exists():
        return 0
    return sum(1 for p in docs.glob("*/index.html"))


def _heartbeat_loop():
    """Ping de vida cada HEARTBEAT_MIN minutos."""
    while True:
        time.sleep(HEARTBEAT_MIN * 60)
        uptime = datetime.now() - _inicio_sesion
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m = rem // 60
        paginas_hoy   = len(_paginas_hoy)
        paginas_total = _count_live_pages()
        telegram(
            f"💓 <b>TrendVortex vivo</b>\n"
            f"Uptime: {h}h {m}m · Ciclo: #{_ciclo_actual}\n"
            f"Nuevas hoy: {paginas_hoy} · Live: {paginas_total}\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )


def iniciar_heartbeat():
    t = threading.Thread(target=_heartbeat_loop, daemon=True)
    t.start()


# ── Informe diario (hilo separado) ────────────────────────────────────────────

def _informe_diario_loop():
    """Envía un resumen cada 24 horas."""
    global _paginas_hoy
    while True:
        time.sleep(INFORME_DIARIO_H * 3600)
        n = len(_paginas_hoy)
        if n == 0:
            telegram(
                f"📊 <b>Informe diario — {datetime.now().strftime('%d/%m/%Y')}</b>\n\n"
                f"0 páginas creadas hoy.\n"
                f"El radar sigue buscando nichos válidos..."
            )
        else:
            links = "\n".join(f"  • <a href='{SITE_URL}/{s}/'>{s.replace('-', ' ').title()}</a>"
                              for s in _paginas_hoy[:10])
            extra = f"\n  ... y {n - 10} más" if n > 10 else ""
            telegram(
                f"📊 <b>Informe diario — {datetime.now().strftime('%d/%m/%Y')}</b>\n\n"
                f"✅ <b>{n} páginas nuevas</b>\n\n"
                f"{links}{extra}\n\n"
                f"🌐 {SITE_URL}"
            )
        _paginas_hoy = []   # reset para el día siguiente


def iniciar_informe_diario():
    t = threading.Thread(target=_informe_diario_loop, daemon=True)
    t.start()


# ── Notificaciones ────────────────────────────────────────────────────────────

def alerta_inicio():
    from markets import get_active
    mercados = ", ".join(get_active().keys()).upper()
    telegram(
        f"🚀 <b>TrendVortex arrancó</b>\n"
        f"Mercados: <code>{mercados}</code>\n"
        f"Radar cada {RADAR_INTERVALO_H}h · Enjambre cada {SWARM_CADA_N_CICLOS} ciclos\n"
        f"💓 Heartbeat cada {HEARTBEAT_MIN} min\n"
        f"🌐 {SITE_URL}"
    )


def alerta_radar(total_leads: int, ciclo: int):
    telegram(
        f"📡 <b>Radar — ciclo #{ciclo}</b>\n"
        f"Nichos nuevos: <b>{total_leads}</b>\n"
        f"🕐 {datetime.now().strftime('%H:%M')}"
    )


def alerta_pagina_nueva(slug: str, keyword: str, comision: float, source: str = ""):
    """Notificación inmediata por cada página publicada."""
    fuente = f" · {source.upper()}" if source else ""
    telegram(
        f"🆕 <b>Página publicada{fuente}</b>\n"
        f"<b>{keyword.title()}</b> — {comision}% comisión\n"
        f"🔗 <a href='{SITE_URL}/{slug}/'>{SITE_URL}/{slug}/</a>"
    )


def alerta_swarm_resumen(deployed: list[str], skipped: int):
    live = _count_live_pages()
    if not deployed:
        telegram(
            f"🤖 Enjambre: 0 nuevas ({skipped} descartados)\n"
            f"📄 Live en sitio: {live} páginas · {SITE_URL}"
        )
        return
    telegram(
        f"✅ <b>Enjambre completo</b>\n"
        f"{len(deployed)} nuevas · {skipped} descartados\n"
        f"📄 Total live: {live} páginas\n"
        f"🌐 {SITE_URL}"
    )


def alerta_error(contexto: str, error: str):
    telegram(
        f"⚠️ <b>Error en TrendVortex</b>\n"
        f"Contexto: {contexto}\n"
        f"Error: {str(error)[:200]}\n"
        f"El loop sigue corriendo."
    )


# ── Paso 1: Radar ─────────────────────────────────────────────────────────────

def correr_radar(ciclo: int) -> int:
    from radar_nichos import run_ciclo
    leads_antes = _contar_leads()
    print(f"\n{'═'*55}")
    print(f"  [RADAR] Ciclo #{ciclo} — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═'*55}")
    try:
        run_ciclo(ciclo)
    except Exception as e:
        print(f"  [RADAR] Error: {e}")
        alerta_error("radar_nichos", str(e))
    leads_despues = _contar_leads()
    nuevos = max(0, leads_despues - leads_antes)
    print(f"  [RADAR] +{nuevos} leads nuevos (total: {leads_despues})")
    return nuevos


def _contar_leads() -> int:
    p = Path("leads.csv")
    if not p.exists():
        return 0
    try:
        import pandas as pd
        return len(pd.read_csv(p))
    except Exception:
        return 0


# ── Paso 2: Enjambre ──────────────────────────────────────────────────────────

def correr_enjambre(limit: int, markets_override: list[str] | None) -> tuple[list, int]:
    deployed: list[str] = []
    skipped_count = [0]
    try:
        _run_and_capture(limit, markets_override, deployed, skipped_count)
    except Exception as e:
        print(f"  [ENJAMBRE] Error: {e}")
        alerta_error("orchestrator", str(e))
    return deployed, skipped_count[0]


def _run_and_capture(limit, markets_override, deployed_out, skipped_out):
    import orchestrator as orch
    from markets import ACTIVE_MARKETS, ALL_MARKETS

    df = orch.load_leads()
    if df is None:
        return

    market_codes = markets_override or ACTIVE_MARKETS
    active       = {k: ALL_MARKETS[k] for k in market_codes if k in ALL_MARKETS}
    memory       = orch.SwarmMemory()
    agents       = orch.build_agents()

    from learning.niche_learner import NicheLearner
    learner = NicheLearner()
    df = learner.rank_and_filter_leads(df)

    cap   = orch.MAX_PAGES_PER_RUN if orch.MAX_PAGES_PER_RUN > 0 else len(df)
    total = min(cap, len(df)) if not limit else min(limit, len(df), cap)

    for market_code, market in active.items():
        df_m = df.head(total).copy()
        df_m["market"] = market_code
        for _, row in df_m.iterrows():
            page_slugs = orch.process_lead(row, agents, memory, learner=learner)
            if page_slugs:
                for slug in page_slugs:
                    full = f"{market['site_prefix']}/{slug}" if market["site_prefix"] else slug
                    deployed_out.append(full)
                    _paginas_hoy.append(full)

                    # Notificación inmediata con el link
                    kw       = str(row.get("keyword", slug.replace("-", " ")))
                    comision = float(row.get("comision_pct", 3.0))
                    source   = "ebay" if slug.endswith("-ebay") else "amazon"
                    alerta_pagina_nueva(full, kw, comision, source)
            else:
                skipped_out[0] += 1
            time.sleep(orch.LEAD_SLEEP_SECONDS)

    if deployed_out:
        orch.deploy_github(deployed_out)
        from orchestrator import AgentType, Episode
        for s in deployed_out:
            kw = s.split("/")[-1].replace("-", " ")
            memory.add(Episode(
                timestamp=datetime.now().isoformat(),
                agent_type=AgentType.DEPLOY.value,
                keyword=kw, action="DEPLOYED", score=80,
                reasoning=f"{SITE_URL}/{s}/",
                payload={"slug": s},
            ))


# ── Loop principal ────────────────────────────────────────────────────────────

def main(limit: int = 0, markets_str: str = "", once: bool = False):
    global _ciclo_actual
    markets_list = [m.strip() for m in markets_str.split(",") if m.strip()] or None

    iniciar_heartbeat()
    iniciar_informe_diario()
    alerta_inicio()

    ciclo = 1

    while True:
        _ciclo_actual = ciclo

        # ── Capa 0: Macro Radar (cada 24h) ────────────────────────────────────
        if ciclo % MACRO_CADA_N_CICLOS == 1:
            telegram(f"🌍 <b>Macro Radar arrancando</b> — ciclo #{ciclo}\nFRED · BanRep · Eurostat · Trends")
            try:
                from macro_radar import MacroRadar
                from markets import ACTIVE_MARKETS
                mr = MacroRadar()
                kws = mr.run(markets=ACTIVE_MARKETS)
                telegram(
                    f"🌍 <b>Macro Radar completo</b>\n"
                    f"{len(kws)} keywords priorizados por señales macro\n"
                    f"Top 3: {' · '.join(k.keyword for k in kws[:3])}"
                )
            except Exception as e:
                print(f"  [MACRO] Error: {e}")
                alerta_error("macro_radar", str(e))

        # ── Capa 1: Radar Reddit + fallback offline ────────────────────────────
        nuevos = correr_radar(ciclo)
        # Si el radar no encontró nada (rate limit / sin nichos), usar modo offline
        if nuevos == 0:
            try:
                from macro_radar import MacroRadar
                from markets import ACTIVE_MARKETS
                mr = MacroRadar()
                kws = mr.run_offline(markets=ACTIVE_MARKETS, top_n=30)
                nuevos_offline = len(kws)
                print(f"  [MACRO OFFLINE] {nuevos_offline} leads inyectados en leads.csv")
            except Exception as e:
                print(f"  [MACRO OFFLINE] Error: {e}")
        alerta_radar(nuevos, ciclo)

        # ── Enjambre ──────────────────────────────────────────────────────────
        if ciclo % SWARM_CADA_N_CICLOS == 0:
            deployed, skipped = correr_enjambre(limit, markets_list)
            alerta_swarm_resumen(deployed, skipped)

        if once:
            if ciclo % SWARM_CADA_N_CICLOS != 0:
                deployed, skipped = correr_enjambre(limit, markets_list)
                alerta_swarm_resumen(deployed, skipped)
            print("\n  Modo --once: saliendo.")
            break

        proxima = datetime.fromtimestamp(time.time() + RADAR_INTERVALO_H * 3600)
        print(f"\n  Próximo ciclo: {proxima.strftime('%H:%M')} ({RADAR_INTERVALO_H}h)")
        telegram(f"💤 Durmiendo {RADAR_INTERVALO_H}h · próximo ciclo: {proxima.strftime('%H:%M')}")
        time.sleep(RADAR_INTERVALO_H * 3600)
        ciclo += 1


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrendVortex — Loop autónomo")
    parser.add_argument("--limit",   type=int, default=0)
    parser.add_argument("--markets", type=str, default="")
    parser.add_argument("--once",    action="store_true")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════╗")
    print("║          TrendVortex — Loop Autónomo                ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"  Radar cada    : {RADAR_INTERVALO_H}h")
    print(f"  Enjambre cada : {SWARM_CADA_N_CICLOS} ciclos")
    print(f"  Heartbeat     : cada {HEARTBEAT_MIN} min")
    print(f"  Informe diario: cada {INFORME_DIARIO_H}h")
    print(f"  Límite págs   : {args.limit or 'sin límite'}")
    print()

    main(limit=args.limit, markets_str=args.markets, once=args.once)
