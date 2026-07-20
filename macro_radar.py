# -*- coding: utf-8 -*-
"""
macro_radar.py — Inteligencia Macro de Consumo
Capa 0 del pipeline TrendVortex.

Fuentes de datos:
  - Google Trends    : trending diario + señal regional + queries relacionadas
  - FRED (Fed USA)   : gasto del consumidor, ingreso, confianza, ventas retail
  - BanRep (Colombia): confianza del consumidor, cartera, empleo
  - Eurostat (UE)    : confianza, ventas retail, consumo de hogares

Salida: cola priorizada de keywords con score macro por región.
El score combina:
  - Velocidad de tendencia (Trends slope)
  - Ingreso disponible de la región
  - Sentimiento del consumidor
  - Boost estacional
  - Comisión Amazon de la categoría

Uso:
  python macro_radar.py                 # corre todas las fuentes
  python macro_radar.py --source fred   # solo FRED
  python macro_radar.py --source trends # solo Trends
  python macro_radar.py --top 20        # top 20 keywords
"""
from __future__ import annotations
import os, sys, time, json, calendar
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

import requests

from keyword_filter import es_keyword_producto

# ── Patch urllib3 para pytrends ───────────────────────────────────────────────
try:
    import urllib3.util.retry as _retry_mod
    _orig = _retry_mod.Retry.__init__
    def _patched(self, *a, method_whitelist=None, **kw):
        if method_whitelist is not None and "allowed_methods" not in kw:
            kw["allowed_methods"] = method_whitelist
        _orig(self, *a, **kw)
    _retry_mod.Retry.__init__ = _patched
except Exception:
    pass

# ── Config ────────────────────────────────────────────────────────────────────
FRED_KEY      = os.getenv("FRED_API_KEY", "")
BANREP_KEY    = os.getenv("BANREP_API_KEY", "")   # opcional — tienen datos públicos
EUROSTAT_KEY  = os.getenv("EUROSTAT_API_KEY", "")  # no requiere key

MACRO_QUEUE_FILE = Path("macro_queue.json")

# Comisión Amazon por categoría → peso en el score
AMAZON_COMMISSION = {
    "Amazon Games":      20.0,
    "Luxury Beauty":     10.0,
    "Pet Supplies":       5.0,
    "Kitchen & Dining":  4.5,
    "Automotive":        4.5,
    "Home Improvement":  4.5,
    "Fashion":           4.0,
    "Sports & Outdoors": 3.0,
    "Toys & Baby":       3.0,
    "General":           3.0,
}

# Mapa: término de tendencia → categoría Amazon
TREND_CATEGORY_MAP = {
    "skin care": "Luxury Beauty",   "sunscreen": "Luxury Beauty",
    "serum": "Luxury Beauty",        "moisturizer": "Luxury Beauty",
    "foundation": "Luxury Beauty",   "mascara": "Luxury Beauty",
    "eyeliner": "Luxury Beauty",     "lipstick": "Luxury Beauty",
    "hair": "Luxury Beauty",         "shampoo": "Luxury Beauty",
    "coffee": "Kitchen & Dining",    "sous vide": "Kitchen & Dining",
    "air fryer": "Kitchen & Dining", "knife": "Kitchen & Dining",
    "cookware": "Kitchen & Dining",  "blender": "Kitchen & Dining",
    "grill": "Kitchen & Dining",     "espresso": "Kitchen & Dining",
    "keyboard": "Amazon Games",      "mouse": "Amazon Games",
    "gaming": "Amazon Games",        "headset": "Amazon Games",
    "gpu": "Amazon Games",           "monitor": "Amazon Games",
    "dog": "Pet Supplies",           "cat": "Pet Supplies",
    "pet": "Pet Supplies",           "aquarium": "Pet Supplies",
    "camping": "Sports & Outdoors",  "hiking": "Sports & Outdoors",
    "running": "Sports & Outdoors",  "cycling": "Sports & Outdoors",
    "fitness": "Sports & Outdoors",  "yoga": "Sports & Outdoors",
    "vacuum": "Home Improvement",    "dehumidifier": "Home Improvement",
    "mattress": "Home Improvement",  "pillow": "Home Improvement",
    "car": "Automotive",             "dashcam": "Automotive",
    "detailing": "Automotive",       "tire": "Automotive",
    "sneaker": "Fashion",            "wallet": "Fashion",
    "watch": "Fashion",              "backpack": "Fashion",
    "toy": "Toys & Baby",            "baby": "Toys & Baby",
    "stroller": "Toys & Baby",
}

# Boost estacional por mes → categorías favorecidas
SEASONAL_BOOST: dict[int, dict[str, float]] = {
    1:  {"Home Improvement": 1.3, "Fitness": 1.5, "Sports & Outdoors": 1.2},   # Jan
    2:  {"Luxury Beauty": 1.4, "Fashion": 1.3},                                  # Feb Valentine
    3:  {"Sports & Outdoors": 1.3, "Kitchen & Dining": 1.2},                    # Mar
    4:  {"Sports & Outdoors": 1.4, "Home Improvement": 1.3},                    # Apr spring
    5:  {"Sports & Outdoors": 1.3, "Automotive": 1.2},                          # May
    6:  {"Sports & Outdoors": 1.5, "Automotive": 1.3, "Luxury Beauty": 1.2},   # Jun summer
    7:  {"Sports & Outdoors": 1.5, "Automotive": 1.2},                          # Jul
    8:  {"Amazon Games": 1.3, "Toys & Baby": 1.2},                              # Aug back-to-school
    9:  {"Amazon Games": 1.2, "Kitchen & Dining": 1.2},                         # Sep
    10: {"Amazon Games": 1.5, "Toys & Baby": 1.4, "Home Improvement": 1.3},    # Oct pre-holiday
    11: {"Amazon Games": 1.8, "Toys & Baby": 1.6, "Kitchen & Dining": 1.5,
         "Fashion": 1.4, "Luxury Beauty": 1.4},                                 # Nov BlackFriday
    12: {"Amazon Games": 1.8, "Toys & Baby": 1.7, "Fashion": 1.5,
         "Luxury Beauty": 1.5, "Kitchen & Dining": 1.4},                        # Dec
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class MacroSignal:
    """Una señal macro de una fuente específica."""
    source:     str               # fred | banrep | eurostat | gtrends
    region:     str               # US | CO | EU | Texas | etc.
    indicator:  str               # UMCSENT | ICC | consumer_sentiment
    value:      float             # valor actual
    change_pct: float = 0.0       # cambio % vs período anterior
    period:     str = ""          # "2026-05" / "Q1-2026"
    note:       str = ""

@dataclass
class MacroKeyword:
    """Keyword con score macro compuesto."""
    keyword:      str
    category:     str
    commission:   float
    macro_score:  float           # 0–100
    trend_score:  float = 0.0     # de Google Trends
    macro_boost:  float = 1.0     # multiplicador de señales macro
    seasonal_boost: float = 1.0
    regions:      list[str] = field(default_factory=list)
    signals:      list[MacroSignal] = field(default_factory=list)
    source:       str = ""        # trending | fred_category | banrep | eurostat

    def to_lead_row(self) -> dict:
        return {
            "keyword":      self.keyword,
            "amazon_cat":   self.category,
            "comision_pct": self.commission,
            "hits_max":     self.trend_score,
            "hits_reciente":self.trend_score,
            "slope":        self.macro_score / 10,
            "trending":     True,
            "titulo":       f"[MACRO] {self.keyword}",
            "url":          f"macro://{self.source}/{self.keyword.replace(' ','-')}",
            "subreddit":    "macro_radar",
            "macro_score":  self.macro_score,
            "regions":      ",".join(self.regions[:3]),
        }


# ══════════════════════════════════════════════════════════════════════════════
# FUENTE 1 — GOOGLE TRENDS (señal directa de búsqueda)
# ══════════════════════════════════════════════════════════════════════════════

class GTrendsSource:
    """
    Google Trends como fuente primaria — no validador.
    - trending_searches(): qué está explotando hoy
    - interest_by_region(): dónde se busca más
    - related_queries(): keywords satélite con potencial
    """
    COUNTRIES = {
        "us": "united_states", "es": "spain", "mx": "mexico",
        "co": "colombia",      "ar": "argentina", "de": "germany",
        "fr": "france",        "br": "brazil",    "gb": "united_kingdom",
    }

    def __init__(self):
        from pytrends.request import TrendReq
        self.pt = TrendReq(hl="en-US", tz=360, timeout=(10, 30),
                           retries=2, backoff_factor=1.5)

    # Seeds por categoría Amazon → pytrends saca las rising queries satélite
    CATEGORY_SEEDS: dict[str, list[str]] = {
        "Luxury Beauty":     ["best serum face", "sunscreen spf", "skin care routine"],
        "Kitchen & Dining":  ["air fryer", "coffee maker espresso", "sous vide cooker"],
        "Amazon Games":      ["mechanical keyboard", "gaming mouse", "gaming headset"],
        "Pet Supplies":      ["best dog food", "cat litter", "pet camera"],
        "Sports & Outdoors": ["running shoes", "camping gear", "yoga mat"],
        "Automotive":        ["dashcam", "car seat cover", "car detailing kit"],
        "Home Improvement":  ["robot vacuum", "air purifier", "dehumidifier home"],
        "Fashion":           ["minimalist watch", "leather wallet men", "running sneakers"],
        "Toys & Baby":       ["baby monitor", "toddler toys", "stroller lightweight"],
    }

    GEO_MAP = {
        "us": "US", "es": "ES", "mx": "MX", "co": "CO",
        "ar": "AR", "de": "DE", "fr": "FR", "br": "BR", "gb": "GB",
    }

    def trending_now(self, markets: list[str] = None) -> list[MacroKeyword]:
        """
        Encuentra queries de producto en auge usando seeds por categoría.
        Para cada categoría toma un seed → related_queries 'rising' → keywords reales.
        """
        markets = markets or ["us", "es", "co"]
        geo     = self.GEO_MAP.get(markets[0], "US")   # primario = primer mercado
        results: list[MacroKeyword] = []
        seen    = set()

        for cat, seeds in self.CATEGORY_SEEDS.items():
            com = AMAZON_COMMISSION.get(cat, 3.0)
            seed = seeds[0]   # seed principal de la categoría
            print(f"  [GTrends] Explorando '{cat}' via '{seed}'...")
            try:
                time.sleep(12)   # respetar rate limit
                self.pt.build_payload([seed], timeframe="today 3-m", geo=geo)
                related = self.pt.related_queries()
                rising  = related.get(seed, {}).get("rising")
                if rising is None or rising.empty:
                    # fallback: validar el seed directamente
                    series = self.validate_series(seed, geo)
                    if series and series["trending"]:
                        if seed not in seen:
                            seen.add(seed)
                            results.append(MacroKeyword(
                                keyword=seed, category=cat, commission=com,
                                macro_score=70.0,
                                trend_score=series["hits_reciente"],
                                regions=[geo], source="gtrends_seed",
                            ))
                            print(f"  [GTrends] ✓ seed '{seed}' trending")
                    continue

                for _, row in rising.head(5).iterrows():
                    query = str(row.get("query","")).strip().lower()
                    value = float(row.get("value", 0))
                    if not query or query in seen or len(query) < 4:
                        continue
                    seen.add(query)
                    score = min(100.0, 50.0 + value / 4)
                    results.append(MacroKeyword(
                        keyword=query, category=cat, commission=com,
                        macro_score=70.0, trend_score=score,
                        regions=[geo], source="gtrends_rising",
                    ))
                    print(f"  [GTrends] ↑ '{query}' ({cat} {com}%) rising={value:.0f}%")

            except Exception as e:
                print(f"  [GTrends] Error {cat}: {e}")

        return results

    def regional_signal(self, keyword: str) -> dict[str, float]:
        """
        Devuelve interest score por región (estado/país).
        Útil para geo-targeting: saber que Florida busca más 'robot vacuum'.
        """
        try:
            time.sleep(6)
            self.pt.build_payload([keyword], timeframe="today 3-m", geo="US")
            df = self.pt.interest_by_region(resolution="REGION", inc_low_vol=True)
            if df is None or df.empty:
                return {}
            top = df.nlargest(5, keyword)
            return {row["geoName"]: float(row[keyword])
                    for _, row in top.iterrows() if row[keyword] > 20}
        except Exception as e:
            print(f"  [GTrends] Error regional '{keyword}': {e}")
            return {}

    def related_rising(self, keyword: str) -> list[str]:
        """Queries relacionadas en auge — expande el keyword set."""
        try:
            time.sleep(8)
            self.pt.build_payload([keyword], timeframe="today 3-m")
            related = self.pt.related_queries()
            rising = related.get(keyword, {}).get("rising")
            if rising is None or rising.empty:
                return []
            return rising["query"].tolist()[:5]
        except Exception as e:
            print(f"  [GTrends] Error related '{keyword}': {e}")
            return []

    def validate_series(self, keyword: str, geo: str = "US") -> Optional[dict]:
        """Validación clásica de serie temporal (reemplaza el uso en radar_nichos)."""
        try:
            time.sleep(10)
            self.pt.build_payload([keyword], timeframe="today 3-m", geo=geo)
            df = self.pt.interest_over_time()
            if df is None or df.empty or keyword not in df.columns:
                return None
            serie = df[keyword].tolist()
            if len(serie) < 8:
                return None
            hits_max      = max(serie)
            hits_reciente = round(sum(serie[-4:]) / 4, 1)
            hits_previo   = round(sum(serie[-12:-4]) / 8, 1)
            slope         = round(hits_reciente - hits_previo, 1)
            return {
                "hits_max": hits_max, "hits_reciente": hits_reciente,
                "slope": slope, "trending": hits_reciente >= 50 or slope > 8,
            }
        except Exception as e:
            print(f"  [GTrends] Error series '{keyword}': {e}")
            return None

    def _classify(self, term: str) -> tuple[str, float]:
        t = term.lower()
        for kw, cat in TREND_CATEGORY_MAP.items():
            if kw in t:
                return cat, AMAZON_COMMISSION.get(cat, 3.0)
        return "General", 3.0


# ══════════════════════════════════════════════════════════════════════════════
# FUENTE 1b — GOOGLE TRENDS RSS (sin librería, sin rate limit)
# ══════════════════════════════════════════════════════════════════════════════
# pytrends fue archivada en Abril 2025 → reemplazada por el RSS oficial
# de Google Trends (el mismo feed que impulsa trends.google.com/trending)

class GTrendsRSSSource:
    """
    Google Trends diarios via RSS — cero dependencias externas, cero rate limits.
    Endpoint público: trends.google.com/trends/trendingsearches/daily/rss

    Ventajas vs pytrends:
      - No requiere librería (usa requests + xml.etree nativo)
      - Google mantiene este feed activamente (usa en la app Trending Searches)
      - Retorna volumen absoluto aproximado (ht:approx_traffic)
      - 0 ms de warmup vs 10–12 s de pytrends por categoría
    """
    RSS_URL = "https://trends.google.com/trends/trendingsearches/daily/rss"
    HT_NS   = "https://trends.google.com/trends/trendingsearches/daily"

    GEO_MAP = {
        "us": "US", "gb": "GB", "es": "ES", "mx": "MX", "co": "CO",
        "ar": "AR", "de": "DE", "fr": "FR", "br": "BR", "it": "IT",
    }

    def trending_now(self, markets: list[str] = None) -> list[MacroKeyword]:
        markets = markets or ["us", "es"]
        results: list[MacroKeyword] = []
        seen: set[str] = set()
        got_live_data = False

        for market in markets[:2]:
            geo = self.GEO_MAP.get(market, "US")
            try:
                items = self._fetch_trending(geo)
                got_live_data = True
                for term, volume in items[:25]:
                    term_lower = term.lower()
                    if term_lower in seen or len(term) < 4:
                        continue
                    seen.add(term_lower)
                    cat, com = self._classify(term_lower)
                    if cat == "General":
                        continue
                    score = min(100.0, 35.0 + min(volume / 80_000, 65.0))
                    results.append(MacroKeyword(
                        keyword=term_lower, category=cat, commission=com,
                        macro_score=score, trend_score=score,
                        regions=[geo], source="gtrends_live",
                    ))
                    print(f"  [GTrends] ↑ '{term}' ({cat} {com}%)")
            except Exception as e:
                print(f"  [GTrends] Error geo={geo}: {e}")

        # Fallback: Gemini genera keywords por estacionalidad
        if not got_live_data or len(results) < 5:
            print("  [GTrends] Activando fallback Gemini AI para tendencias...")
            gemini_items = self.gemini_trending(top_n=20)
            for item_tuple in gemini_items:
                term, score = item_tuple[0], item_tuple[1]
                gemini_cat  = item_tuple[2] if len(item_tuple) > 2 else ""
                if term in seen:
                    continue
                seen.add(term)
                cat, com = self._classify(term)
                # Si classify no encontró categoría pero Gemini sí la dio, usar la de Gemini
                if cat == "General" and gemini_cat in AMAZON_COMMISSION:
                    cat = gemini_cat
                    com = AMAZON_COMMISSION[cat]
                results.append(MacroKeyword(
                    keyword=term, category=cat, commission=com,
                    macro_score=float(score), trend_score=float(score),
                    regions=["US"], source="gemini_trend",
                ))

        return results

    def _fetch_trending(self, geo: str = "US") -> list[tuple[str, int]]:
        """
        Intenta múltiples endpoints de Google Trends (los URLs cambian periódicamente).
        Retorna lista de (término, volumen_aproximado).
        """
        import xml.etree.ElementTree as ET
        import re

        hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        # Endpoint 1: RSS diario (URL 2024+)
        rss_urls = [
            f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}&hl=en-US",
            f"https://trends.google.com/trends/trendingsearches/realtime/rss?geo={geo}&hl=en-US&cat=all",
        ]
        for url in rss_urls:
            try:
                r = requests.get(url, headers=hdrs, timeout=12)
                if r.status_code == 200:
                    root = ET.fromstring(r.content)
                    ns_map = {"ht": self.HT_NS}
                    items = []
                    for item in root.iter("item"):
                        title_el   = item.find("title")
                        traffic_el = item.find("ht:approx_traffic", ns_map)
                        if title_el is None or not title_el.text:
                            continue
                        term = title_el.text.strip()
                        volume = 0
                        if traffic_el is not None and traffic_el.text:
                            try:
                                volume = int(traffic_el.text.replace(",", "").replace("+", "").strip())
                            except ValueError:
                                pass
                        items.append((term, volume))
                    if items:
                        print(f"  [GTrends] RSS OK: {len(items)} términos desde {url[:60]}...")
                        return items
            except Exception:
                pass

        # Endpoint 2: API JSON interno (usado por trends.google.com)
        try:
            r = requests.get(
                "https://trends.google.com/trends/api/dailytrends",
                params={"hl": "en-US", "tz": "-180", "geo": geo, "ns": "15"},
                headers=hdrs, timeout=12,
            )
            if r.status_code == 200:
                # La respuesta empieza con ")]}',\n" — remover ese prefijo
                text = r.text
                if text.startswith(")]}'"):
                    text = text[text.index("\n") + 1:]
                data = json.loads(text)
                topics = (data.get("default", {})
                              .get("trendingSearchesDays", [{}])[0]
                              .get("trendingSearches", []))
                items = []
                for t in topics:
                    title = t.get("title", {}).get("query", "")
                    vol_str = t.get("formattedTraffic", "0")
                    try:
                        volume = int(re.sub(r"[^\d]", "", vol_str)) * (
                            1000 if "K" in vol_str else (1_000_000 if "M" in vol_str else 1)
                        )
                    except Exception:
                        volume = 0
                    if title:
                        items.append((title, volume))
                if items:
                    print(f"  [GTrends] JSON API OK: {len(items)} términos")
                    return items
        except Exception as e:
            print(f"  [GTrends] JSON API error: {e}")

        raise RuntimeError(f"Todos los endpoints de Google Trends fallaron para {geo}")

    # ── fallback: Gemini genera trending keywords por estacionalidad ──────────
    @staticmethod
    def gemini_trending(month: int = None, top_n: int = 20) -> list[tuple]:
        """
        Usa Gemini Flash (REST API directa) para sugerir trending Amazon keywords.
        Fallback cuando Google Trends está bloqueado.
        Usa thinkingBudget=0 para no desperdiciar tokens en razonamiento.
        Retorna: [(keyword, score, category), ...]
        """
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
            return []

        month = month or datetime.now().month
        month_names = {
            1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
            7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"
        }
        mon_name = month_names.get(month, "June")
        year     = datetime.now().year

        prompt = (
            f"It is {mon_name} {year}. "
            f"List {top_n} specific Amazon product search keywords trending RIGHT NOW "
            f"due to seasonal demand or consumer trends. "
            f"Valid categories: Kitchen & Dining, Amazon Games, Luxury Beauty, "
            f"Pet Supplies, Sports & Outdoors, Automotive, Home Improvement, Fashion, Toys & Baby. "
            f'Return ONLY a JSON array: [{{"keyword":"portable fan","score":82,"category":"Home Improvement"}},...] '
            f"Score 0-100 = current demand. No explanation outside JSON."
        )

        try:
            r = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.5-flash:generateContent",
                params={"key": gemini_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature":     0.3,
                        "maxOutputTokens": 2048,
                        "thinkingConfig":  {"thinkingBudget": 0},
                    },
                },
                timeout=25,
            )
            if r.status_code != 200:
                print(f"  [Gemini Trends] HTTP {r.status_code}: {r.text[:120]}")
                return []

            text  = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            start = text.find("[")
            end   = text.rfind("]")
            if start == -1 or end <= start:
                print(f"  [Gemini Trends] Sin JSON array (len={len(text)}): {text[:80]}")
                return []

            data  = json.loads(text[start:end + 1])
            items = []
            for item in data:
                kw    = str(item.get("keyword", "")).strip().lower()
                score = int(item.get("score", 50))
                cat   = str(item.get("category", ""))
                if kw and len(kw) > 3:
                    items.append((kw, score, cat))
            print(f"  [Gemini Trends] {len(items)} keywords generados por IA")
            return items

        except Exception as e:
            print(f"  [Gemini Trends] Error: {e}")
            return []

    def _classify(self, term: str) -> tuple[str, float]:
        for kw, cat in TREND_CATEGORY_MAP.items():
            if kw in term:
                return cat, AMAZON_COMMISSION.get(cat, 3.0)
        return "General", 3.0


# ══════════════════════════════════════════════════════════════════════════════
# FUENTE 1c — RAINFOREST BESTSELLERS (Amazon Top 10 por categoría)
# ══════════════════════════════════════════════════════════════════════════════
# Señal más directa posible: lo que más se VENDE en Amazon hoy.
# Usa la misma key de Rainforest que amazon_checker.py.
# Cachea 24h para no consumir la cuota mensual de 100 calls.

class RainforestBestsellersSource:
    """
    Lee los Amazon Bestsellers por categoría vía Rainforest API.
    Convierte títulos de producto en keywords buscables para el pipeline.

    Rate limit: el plan free tiene 100 calls/mes.
    Estrategia: max 2 categorías/run, caché de 24h → ≤ 60 calls/mes.
    """
    CACHE_FILE = Path("bestsellers_cache.json")
    CACHE_TTL_H = 24  # horas

    # Amazon category node IDs en amazon.com
    CATEGORY_IDS: dict[str, str] = {
        "Kitchen & Dining":  "284507",
        "Amazon Games":      "468642",
        "Sports & Outdoors": "3375251",
        "Luxury Beauty":     "3760911",
        "Pet Supplies":      "2619534",
        "Automotive":        "15684181",
        "Toys & Baby":       "165796011",
        "Home Improvement":  "1055398",
        "Fashion":           "7141123",
    }

    # Rotación de categorías para distribuir las calls a lo largo del día
    ROTATION_ORDER = [
        "Luxury Beauty",      # comisión 10%
        "Amazon Games",       # comisión 20%
        "Kitchen & Dining",   # comisión 4.5%
        "Pet Supplies",       # comisión 5%
        "Sports & Outdoors",  # comisión 3%
        "Automotive",         # comisión 4.5%
        "Home Improvement",   # comisión 4.5%
        "Fashion",            # comisión 4%
        "Toys & Baby",        # comisión 3%
    ]

    def __init__(self):
        self.key = os.getenv("RAINFOREST_KEY", "")

    def get_bestsellers(self, max_calls: int = 2) -> list[MacroKeyword]:
        """
        Retorna keywords extraídos de los Amazon Bestsellers.
        Cachea por 24h para preservar cuota de Rainforest.
        """
        if not self.key:
            print("  [RF Bestsellers] Sin RAINFOREST_KEY — saltando")
            return []

        cache = self._load_cache()
        results: list[MacroKeyword] = []
        seen: set[str] = set()
        calls_made = 0

        # Determinar qué categorías ya están en caché válido
        for cat in self.ROTATION_ORDER:
            if calls_made >= max_calls:
                break
            if self._cache_fresh(cache, cat):
                # Usar datos en caché
                for item in cache.get(cat, {}).get("items", []):
                    kw = item["keyword"]
                    if kw in seen:
                        continue
                    seen.add(kw)
                    results.append(MacroKeyword(
                        keyword=kw,
                        category=cat,
                        commission=AMAZON_COMMISSION.get(cat, 3.0),
                        macro_score=item["score"],
                        trend_score=item["score"],
                        regions=["US"],
                        source="rf_bestseller_cache",
                    ))
                continue

            # Fetch desde API
            cat_id = self.CATEGORY_IDS.get(cat)
            if not cat_id:
                continue
            try:
                print(f"  [RF Bestsellers] Consultando #{cat} (id={cat_id})...")
                time.sleep(1.5)
                resp = requests.get(
                    "https://api.rainforestapi.com/request",
                    params={
                        "api_key":        self.key,
                        "type":           "bestsellers",
                        "amazon_domain":  "amazon.com",
                        "category_id":    cat_id,
                        "page":           1,
                    },
                    timeout=20,
                )
                calls_made += 1
                if resp.status_code == 200:
                    raw = resp.json().get("bestsellers", [])
                    items_data, cat_keywords = self._parse_bestsellers(raw, cat)
                    cache[cat] = {
                        "fetched_at": datetime.now().isoformat(),
                        "items": items_data,
                    }
                    self._save_cache(cache)
                    for kw_obj in cat_keywords:
                        if kw_obj.keyword not in seen:
                            seen.add(kw_obj.keyword)
                            results.append(kw_obj)
                else:
                    print(f"  [RF Bestsellers] HTTP {resp.status_code} para {cat}")
            except Exception as e:
                print(f"  [RF Bestsellers] Error {cat}: {e}")

        return results

    def _parse_bestsellers(self, raw: list[dict], cat: str) -> tuple[list[dict], list[MacroKeyword]]:
        com = AMAZON_COMMISSION.get(cat, 3.0)
        items_data: list[dict] = []
        keywords: list[MacroKeyword] = []

        for item in raw[:12]:
            titulo  = item.get("title", "")
            rank    = item.get("rank", 99)
            rating  = item.get("rating", 4.0) or 4.0
            reviews = item.get("ratings_total", 0) or 0

            if not titulo or len(titulo) < 5:
                continue

            kw = self._title_to_keyword(titulo)
            if not kw:
                continue

            rank_score   = max(0.0, 100.0 - (rank - 1) * 7.5)
            review_score = min(25.0, reviews / 800)
            score        = min(100.0, rank_score * 0.65 + review_score + rating * 4)

            items_data.append({"keyword": kw, "score": round(score, 1)})
            keywords.append(MacroKeyword(
                keyword=kw, category=cat, commission=com,
                macro_score=score, trend_score=score,
                regions=["US"], source="rf_bestseller",
            ))
            print(f"  [RF Bestsellers] #{rank:>2} '{kw[:38]}' ({cat}) → score={score:.0f}")

        return items_data, keywords

    def _title_to_keyword(self, titulo: str) -> str:
        import re
        STOPWORDS = {
            "the", "for", "with", "and", "or", "in", "of", "to", "a", "an",
            "inch", "pack", "set", "new", "best", "top", "premium", "pro",
            "plus", "max", "xl", "2024", "2025", "2026", "model", "edition",
            "version", "series", "ultra", "mini", "deluxe", "bundle", "piece",
            "count", "oz", "lbs", "lb", "kg", "g", "ml", "pack", "ct",
        }
        clean = re.sub(r"[^\w\s]", " ", titulo).strip().lower()
        words = [w for w in clean.split() if w not in STOPWORDS and len(w) > 2 and not w.isdigit()]
        significant = words[:4]
        return " ".join(significant) if significant else ""

    def _load_cache(self) -> dict:
        try:
            if self.CACHE_FILE.exists():
                return json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_cache(self, cache: dict):
        try:
            self.CACHE_FILE.write_text(
                json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _cache_fresh(self, cache: dict, cat: str) -> bool:
        entry = cache.get(cat, {})
        if not entry.get("fetched_at"):
            return False
        try:
            fetched = datetime.fromisoformat(entry["fetched_at"])
            age_h   = (datetime.now() - fetched).total_seconds() / 3600
            return age_h < self.CACHE_TTL_H
        except Exception:
            return False


# ══════════════════════════════════════════════════════════════════════════════
# FUENTE 2 — FRED API (Reserva Federal EE.UU.)
# ══════════════════════════════════════════════════════════════════════════════

class FREDSource:
    """
    Federal Reserve Economic Data — St. Louis Fed.
    API key gratuita en: fred.stlouisfed.org/docs/api/api_key.html

    Series clave para predecir consumo:
      UMCSENT   — Confianza del Consumidor (U of Michigan) → proxy de disposición a gastar
      DSPIC96   — Ingreso Personal Disponible Real → poder de compra
      PCE       — Gasto Personal en Consumo → qué gastan
      PCEDG     — PCE Bienes Duraderos → electrónicos, electrodomésticos
      PCEND     — PCE Bienes No Duraderos → ropa, cuidado personal
      RETAILSL  — Ventas Retail → señal directa de compra
      UNRATE    — Desempleo → contexto macro
    """
    BASE = "https://api.stlouisfed.org/fred"

    # Serie → categoría Amazon más afín
    SERIES_CATEGORY = {
        "UMCSENT":  None,             # señal transversal (todas las categorías)
        "DSPIC96":  None,             # señal transversal
        "PCEDG":    ["Amazon Games", "Automotive", "Home Improvement"],
        "PCEND":    ["Luxury Beauty", "Fashion", "Kitchen & Dining"],
        "RETAILSL": None,             # señal transversal
        "UNRATE":   None,             # inverso — alto desempleo = menor consumo
    }

    def __init__(self):
        self.key = FRED_KEY
        if not self.key:
            print("  [FRED] Sin FRED_API_KEY — configura en .env (gratis en fred.stlouisfed.org)")

    def get_series(self, series_id: str, periods: int = 12) -> Optional[MacroSignal]:
        """Descarga la serie y retorna el último valor con cambio %."""
        if not self.key:
            return None
        try:
            r = requests.get(
                f"{self.BASE}/series/observations",
                params={"series_id": series_id, "api_key": self.key,
                        "file_type": "json", "sort_order": "desc",
                        "limit": periods},
                timeout=15
            )
            if r.status_code != 200:
                return None
            obs = [o for o in r.json().get("observations", [])
                   if o["value"] != "."]
            if len(obs) < 2:
                return None
            current = float(obs[0]["value"])
            previous = float(obs[1]["value"])
            change = round((current - previous) / abs(previous) * 100, 2) if previous else 0
            return MacroSignal(
                source="fred", region="US", indicator=series_id,
                value=current, change_pct=change,
                period=obs[0]["date"],
                note=f"{'↑' if change > 0 else '↓'} {abs(change):.1f}% vs período anterior"
            )
        except Exception as e:
            print(f"  [FRED] Error {series_id}: {e}")
            return None

    def macro_boost(self) -> dict[str, float]:
        """
        Calcula multiplicador de boost por categoría basado en señales FRED.
        Retorna dict: categoría → multiplicador (1.0 = neutro, >1 = favorable)
        """
        signals = {}
        for sid in ["UMCSENT", "DSPIC96", "PCEDG", "PCEND", "RETAILSL", "UNRATE"]:
            s = self.get_series(sid, periods=3)
            if s:
                signals[sid] = s
                print(f"  [FRED] {sid}: {s.value:.1f} ({s.note})")
            time.sleep(0.5)

        boost: dict[str, float] = {cat: 1.0 for cat in AMAZON_COMMISSION}

        # Confianza alta → boost en categorías discrecionales (beauty, gaming, fashion)
        if "UMCSENT" in signals:
            sentiment = signals["UMCSENT"].value
            if sentiment > 80:
                for cat in ["Luxury Beauty", "Amazon Games", "Fashion", "Sports & Outdoors"]:
                    boost[cat] = round(boost.get(cat, 1.0) * 1.25, 2)
            elif sentiment < 60:
                for cat in ["Luxury Beauty", "Amazon Games", "Fashion"]:
                    boost[cat] = round(boost.get(cat, 1.0) * 0.85, 2)

        # Ingreso disponible creciendo → boost general, más en categorías caras
        if "DSPIC96" in signals and signals["DSPIC96"].change_pct > 1:
            for cat in AMAZON_COMMISSION:
                boost[cat] = round(boost.get(cat, 1.0) * 1.1, 2)

        # PCE Durable Goods subiendo → gaming, auto, home
        if "PCEDG" in signals and signals["PCEDG"].change_pct > 0:
            for cat in ["Amazon Games", "Automotive", "Home Improvement"]:
                boost[cat] = round(boost.get(cat, 1.0) * 1.15, 2)

        # PCE Non-durable subiendo → beauty, fashion, kitchen
        if "PCEND" in signals and signals["PCEND"].change_pct > 0:
            for cat in ["Luxury Beauty", "Fashion", "Kitchen & Dining"]:
                boost[cat] = round(boost.get(cat, 1.0) * 1.15, 2)

        # Desempleo alto → reducir categorías de lujo
        if "UNRATE" in signals and signals["UNRATE"].value > 5.5:
            for cat in ["Luxury Beauty", "Fashion", "Amazon Games"]:
                boost[cat] = round(boost.get(cat, 1.0) * 0.9, 2)

        return boost

    def state_income(self, state_codes: list[str] = None) -> dict[str, float]:
        """
        Ingreso per cápita por estado (FRED tiene series por estado).
        Devuelve dict: state_code → relative_income_index (100 = media US)
        """
        if not self.key:
            return {}
        state_codes = state_codes or ["CA", "TX", "FL", "NY", "OH"]
        result = {}
        for code in state_codes:
            series_id = f"PCPI{code}"  # Per Capita Personal Income by State
            s = self.get_series(series_id, periods=2)
            if s:
                result[code] = s.value
            time.sleep(0.3)
        # Normalizar a índice 100
        if result:
            avg = sum(result.values()) / len(result)
            result = {k: round(v / avg * 100, 1) for k, v in result.items()}
        return result


# ══════════════════════════════════════════════════════════════════════════════
# FUENTE 3 — BanRep (Banco de la República — Colombia)
# ══════════════════════════════════════════════════════════════════════════════

class BanRepSource:
    """
    Banco de la República de Colombia — API oficial probada en producción.

    Endpoint: suameca.banrep.gov.co/estadisticas-economicas-back/rest/
              estadisticaEconomicaRestService/consultaInformacionSerie?idSerie={id}

    Series IDs confirmados (del Modelo Cuantitativo de Revaliu):
      TRM  = 1      — Tasa Representativa del Mercado COP/USD
      IPC  = 15000  — Índice de Precios al Consumidor
      IPP  = 3      — Índice de Precios del Productor
      TPM  = 59     — Tasa de Política Monetaria BanRep
      IBR  = 241    — IBR overnight

    Respuesta: [{"data": [[timestamp_ms, value], ...]}]
    """
    SERIES_URL = (
        "https://suameca.banrep.gov.co/estadisticas-economicas-back/rest/"
        "estadisticaEconomicaRestService/consultaInformacionSerie"
    )
    SERIES = {
        "TRM": 1,
        "IPC": 15000,
        "IPP": 3,
        "TPM": 59,
        "IBR": 241,
    }

    def _fetch(self, series_id: int, start_year: int = 2015) -> list[tuple]:
        """
        Descarga serie BanRep. Retorna lista ordenada de (fecha_iso, valor).
        start_year limita datos para evitar timestamps históricos problemáticos en Windows.
        """
        import ast
        from urllib.request import Request as UReq, urlopen
        url = f"{self.SERIES_URL}?idSerie={series_id}"
        req = UReq(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
        text = (text.replace("null", "None")
                    .replace("true", "True")
                    .replace("false", "False"))
        payload = ast.literal_eval(text)
        # Timestamp mínimo: 1 Ene del start_year (ms)
        min_ts = int(datetime(start_year, 1, 1).timestamp() * 1000)
        points = []
        for serie in payload:
            for pt in serie.get("data", []):
                if not (isinstance(pt, list) and len(pt) >= 2 and pt[1] is not None):
                    continue
                ts = pt[0]
                if ts < min_ts:
                    continue
                try:
                    # Convertir ms a fecha ISO usando división entera (evita float overflow)
                    seconds = ts // 1000
                    fecha = date.fromtimestamp(seconds).isoformat()
                    points.append((fecha, float(pt[1])))
                except (OSError, OverflowError, ValueError):
                    continue
        return sorted(points)

    def _signal(self, series_id: int, region: str, indicator: str, note_fn) -> Optional[MacroSignal]:
        try:
            pts = self._fetch(series_id)
            if len(pts) < 2:
                return None
            current  = pts[-1][1]
            previous = pts[-2][1]
            change   = round((current - previous) / abs(previous) * 100, 4) if previous else 0
            return MacroSignal(
                source="banrep", region=region, indicator=indicator,
                value=current, change_pct=change,
                period=pts[-1][0],
                note=note_fn(current, change)
            )
        except Exception as e:
            print(f"  [BanRep] Error {indicator}: {e}")
            return None

    def trm(self) -> Optional[MacroSignal]:
        """Tasa Representativa del Mercado USD/COP."""
        return self._signal(
            self.SERIES["TRM"], "CO", "TRM",
            lambda v, c: f"1 USD = {v:,.0f} COP ({'↑' if c > 0 else '↓'}{abs(c):.2f}%)"
        )

    def ipc(self) -> Optional[MacroSignal]:
        """IPC Colombia — inflación anual y mensual."""
        try:
            pts = self._fetch(self.SERIES["IPC"])
            if len(pts) < 13:
                return None
            current   = pts[-1][1]
            prev_1m   = pts[-2][1]
            prev_12m  = pts[-13][1]
            mensual   = round((current - prev_1m)  / abs(prev_1m)  * 100, 2) if prev_1m  else 0
            anual     = round((current - prev_12m) / abs(prev_12m) * 100, 2) if prev_12m else 0
            return MacroSignal(
                source="banrep", region="CO", indicator="IPC",
                value=anual, change_pct=mensual,
                period=pts[-1][0],
                note=f"Inflación CO: {anual:.1f}% anual, {mensual:.2f}% mensual"
            )
        except Exception as e:
            print(f"  [BanRep] IPC error: {e}")
            return None

    def tpm(self) -> Optional[MacroSignal]:
        """Tasa de Política Monetaria BanRep."""
        return self._signal(
            self.SERIES["TPM"], "CO", "TPM",
            lambda v, c: f"TPM: {v:.2f}% ({'bajando' if c < 0 else 'estable/subiendo'})"
        )

    def confidence_index(self) -> Optional[MacroSignal]:
        """
        ICC Colombia — Fedesarrollo vía datos.gov.co.
        Fallback: calcula proxy desde IPC + TPM (inflación alta = menor confianza).
        """
        # Intento 1: datos.gov.co — ICC Fedesarrollo
        try:
            r = requests.get(
                "https://www.datos.gov.co/resource/y7ub-9nuz.json",
                params={"$limit": 3, "$order": "fecha DESC"},
                timeout=12
            )
            if r.status_code == 200 and r.json():
                rows = r.json()
                if rows and "icc" in rows[0]:
                    current  = float(rows[0]["icc"])
                    previous = float(rows[1]["icc"]) if len(rows) > 1 else current
                    change   = round(current - previous, 2)
                    return MacroSignal(
                        source="banrep", region="CO", indicator="ICC_Nacional",
                        value=current, change_pct=change,
                        period=rows[0].get("fecha", ""),
                        note=f"ICC CO={current:.1f} ({'mejora' if change > 0 else 'deteriora'})"
                    )
        except Exception:
            pass

        # Fallback: proxy derivado de TPM + IPC
        ipc_sig = self.ipc()
        tpm_sig = self.tpm()
        if ipc_sig and tpm_sig:
            # Inflación alta + TPM alta = menor confianza (ICC negativo típicamente)
            icc_proxy = -(ipc_sig.value * 0.4 + tpm_sig.value * 0.6) + 20
            return MacroSignal(
                source="banrep", region="CO", indicator="ICC_proxy",
                value=round(icc_proxy, 1), change_pct=0,
                note=f"ICC proxy: inflación={ipc_sig.value:.1f}% TPM={tpm_sig.value:.2f}%"
            )
        return None

    def macro_boost_co(self, icc: Optional[MacroSignal], trm: Optional[MacroSignal],
                       ipc_sig: Optional[MacroSignal] = None,
                       tpm_sig: Optional[MacroSignal] = None) -> dict[str, float]:
        """
        Multiplicador de boost para mercado Colombia.
        - ICC alto → más consumo discrecional
        - TRM alta (dólar caro) → reduce tech importado, favorece locales
        - IPC alto (inflación) → presiona gasto en básicos, reduce discrecional
        - TPM bajando → crédito más barato → más consumo big-ticket
        """
        boost = {cat: 1.0 for cat in AMAZON_COMMISSION}

        # ICC / confianza del consumidor
        if icc and icc.value > 0:
            for cat in ["Kitchen & Dining", "Luxury Beauty", "Fashion", "Pet Supplies"]:
                boost[cat] = round(boost[cat] * 1.15, 2)
        elif icc and icc.value < -10:
            for cat in AMAZON_COMMISSION:
                boost[cat] = round(boost[cat] * 0.9, 2)

        # TRM — dólar caro afecta importaciones
        if trm and trm.value > 4500:
            for cat in ["Amazon Games", "Automotive"]:
                boost[cat] = round(boost[cat] * 0.8, 2)
            for cat in ["Kitchen & Dining", "Pet Supplies"]:
                boost[cat] = round(boost[cat] * 1.1, 2)
        elif trm and trm.value < 3800:  # dólar barato → importados más accesibles
            for cat in ["Amazon Games", "Automotive", "Home Improvement"]:
                boost[cat] = round(boost[cat] * 1.1, 2)

        # IPC — inflación alta comprime gasto discrecional
        if ipc_sig and ipc_sig.value > 8:       # inflación > 8% → aprieta bolsillo
            for cat in ["Luxury Beauty", "Fashion", "Amazon Games"]:
                boost[cat] = round(boost[cat] * 0.85, 2)
        elif ipc_sig and ipc_sig.value < 4:     # inflación controlada → más poder de compra
            for cat in AMAZON_COMMISSION:
                boost[cat] = round(boost[cat] * 1.05, 2)

        # TPM bajando → crédito más barato → big-ticket items
        if tpm_sig and tpm_sig.change_pct < -0.1:  # BanRep bajando tasas
            for cat in ["Automotive", "Home Improvement", "Amazon Games"]:
                boost[cat] = round(boost[cat] * 1.12, 2)

        return boost


# ══════════════════════════════════════════════════════════════════════════════
# FUENTE 4 — EUROSTAT (Unión Europea)
# ══════════════════════════════════════════════════════════════════════════════

class EurostatSource:
    """
    Eurostat — estadísticas oficiales de la Unión Europea.
    API REST pública, sin key requerida.

    Datasets relevantes:
      ei_bcs_cs  — Consumer Confidence Indicator (mensual, por país)
      sts_trtu_m — Retail Trade turnover (ventas retail, por país)
      ilc_mdi07  — Consumo de hogares por categoría de gasto
    """
    BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"

    def consumer_confidence(self, countries: list[str] = None) -> list[MacroSignal]:
        """
        Indicador de Confianza del Consumidor por país EU.
        countries: ['DE', 'FR', 'ES', 'IT', 'NL', 'PL', ...]
        """
        countries = countries or ["DE", "FR", "ES", "IT", "NL"]
        signals = []
        try:
            # Dataset ei_bcs_cs — Consumer Survey
            url = f"{self.BASE}/data/ei_bcs_cs"
            params = {
                "format":      "JSON",
                "lang":        "EN",
                "startPeriod": self._last_n_months(3),
                "indic":       "BS-CSMCI",   # Consumer Confidence
                "s_adj":       "SA",          # seasonally adjusted
                "geo":         "+".join(countries),
            }
            r = requests.get(url, params=params, timeout=20)
            if r.status_code != 200:
                return signals

            data = r.json()
            values_obj  = data.get("value", {})
            dims        = data.get("dimension", {})
            geo_vals    = dims.get("geo", {}).get("category", {}).get("label", {})
            time_vals   = dims.get("time", {}).get("category", {}).get("label", {})

            n_geo   = len(geo_vals)
            n_times = len(time_vals)
            time_labels = list(time_vals.values())
            geo_labels  = list(geo_vals.values())

            for gi, country_name in enumerate(geo_labels):
                # Último período disponible
                for ti in range(n_times - 1, max(-1, n_times - 3), -1):
                    idx = str(gi * n_times + ti)
                    if idx in values_obj:
                        val = float(values_obj[idx])
                        prev_idx = str(gi * n_times + ti - 1)
                        prev = float(values_obj.get(prev_idx, val))
                        change = round(val - prev, 2)
                        signals.append(MacroSignal(
                            source="eurostat", region=list(geo_vals.keys())[gi],
                            indicator="consumer_confidence",
                            value=val, change_pct=change,
                            period=time_labels[ti] if ti < len(time_labels) else "",
                            note=f"{country_name}: confianza {val:.1f}"
                        ))
                        print(f"  [Eurostat] {country_name}: ICC={val:.1f} (Δ{change:+.1f})")
                        break

        except Exception as e:
            print(f"  [Eurostat] Error consumer confidence: {e}")

        return signals

    def retail_sales(self, countries: list[str] = None) -> list[MacroSignal]:
        """Ventas retail por país EU — señal directa de consumo."""
        countries = countries or ["DE", "FR", "ES"]
        signals = []
        try:
            url = f"{self.BASE}/data/sts_trtu_m"
            params = {
                "format":      "JSON",
                "lang":        "EN",
                "startPeriod": self._last_n_months(3),
                "nace_r2":     "G47",         # Retail trade
                "unit":        "I21",          # Index
                "s_adj":       "CA",
                "geo":         "+".join(countries),
            }
            r = requests.get(url, params=params, timeout=20)
            if r.status_code != 200:
                return signals
            data = r.json()
            vals = data.get("value", {})
            dims = data.get("dimension", {})
            geo_vals  = dims.get("geo", {}).get("category", {}).get("label", {})
            for gi, (geo_code, country_name) in enumerate(geo_vals.items()):
                latest = vals.get(str(gi), None)
                if latest is not None:
                    signals.append(MacroSignal(
                        source="eurostat", region=geo_code,
                        indicator="retail_sales_index",
                        value=float(latest), change_pct=0,
                        note=f"{country_name} retail index={latest:.1f}"
                    ))
        except Exception as e:
            print(f"  [Eurostat] Error retail sales: {e}")
        return signals

    def macro_boost_eu(self, signals: list[MacroSignal]) -> dict[str, dict[str, float]]:
        """
        Boost por país EU basado en señales Eurostat.
        Retorna: {'DE': {'Luxury Beauty': 1.2, ...}, 'FR': {...}}
        """
        boost_by_country: dict[str, dict[str, float]] = {}
        for s in signals:
            if s.indicator != "consumer_confidence":
                continue
            country = s.region
            b = {cat: 1.0 for cat in AMAZON_COMMISSION}
            if s.value > 0:      # confianza positiva
                for cat in ["Luxury Beauty", "Fashion", "Amazon Games", "Sports & Outdoors"]:
                    b[cat] = round(b[cat] * 1.2, 2)
            elif s.value < -20:  # confianza muy negativa
                for cat in AMAZON_COMMISSION:
                    b[cat] = round(b[cat] * 0.88, 2)
            if s.change_pct > 2: # mejorando rápido
                for cat in AMAZON_COMMISSION:
                    b[cat] = round(b[cat] * 1.08, 2)
            boost_by_country[country] = b
        return boost_by_country

    def _last_n_months(self, n: int) -> str:
        """Retorna fecha de hace N meses en formato Eurostat (YYYY-MM)."""
        now = datetime.now()
        month = now.month - n
        year  = now.year
        while month <= 0:
            month += 12
            year  -= 1
        return f"{year}-{month:02d}"


# ══════════════════════════════════════════════════════════════════════════════
# FUENTE 5 — E-COMMERCE CYCLES (Amazon/AliExpress — datos públicos 10-K/10-Q)
# ══════════════════════════════════════════════════════════════════════════════

class EcommerceSeasonality:
    """
    Estacionalidad real de e-commerce basada en reportes públicos de Amazon
    y patrones conocidos de AliExpress/Alibaba.

    Fuentes:
      - Amazon 10-K: Q4 (Oct-Dic) = ~35% del revenue anual
      - Amazon 10-K: Q1 = ~20%, Q2 = ~23%, Q3 = ~22%
      - Amazon Prime Day (Jul): gaming/electronics spike +40%
      - Amazon Back-to-School (Ago-Sep): toys/electronics +25%
      - AliExpress 11/11 (Nov): electronics/fashion pico global
      - AliExpress 12/12 (Dic): second wave
      - Black Friday/Cyber Monday (Nov 4ta semana): todo +60-80%
      - Mother's Day (May): beauty/fashion +30%
      - Father's Day (Jun): automotive/sports +25%
      - Valentine's Day (Feb): beauty/fashion +25%
    """

    # Índice de conversión (0-100) por mes — cuánto convierte el tráfico a compra
    CONVERSION_INDEX = {
        1:  65,   # post-holiday cansancio, pero Año Nuevo propósitos
        2:  72,   # Valentine's Day impulso
        3:  68,   # primavera arranque
        4:  70,   # spring shopping
        5:  73,   # Mother's Day
        6:  71,   # Father's Day
        7:  82,   # PRIME DAY — pico artificial Amazon
        8:  75,   # Back to School
        9:  72,   # pre-holiday build-up
        10: 78,   # pre-holiday consciousness
        11: 95,   # BLACK FRIDAY + 11/11 — PICO MÁXIMO
        12: 90,   # Christmas + 12/12
    }

    # Revenue share Amazon por trimestre (fuente: 10-K 2023-2024)
    AMAZON_QUARTERLY_SHARE = {
        "Q1": 0.205,  # Ene-Mar
        "Q2": 0.235,  # Abr-Jun (Prime Day era en Jul, ahora varía)
        "Q3": 0.225,  # Jul-Sep
        "Q4": 0.335,  # Oct-Dic — mayor por mucho
    }

    # Eventos específicos que amplifican categorías
    EVENTS: list[dict] = [
        {"month": 2,  "name": "Valentine's Day",   "cats": ["Luxury Beauty", "Fashion", "Jewelry"], "mult": 1.3},
        {"month": 5,  "name": "Mother's Day",       "cats": ["Luxury Beauty", "Fashion", "Kitchen & Dining"], "mult": 1.35},
        {"month": 6,  "name": "Father's Day",       "cats": ["Automotive", "Sports & Outdoors", "Amazon Games"], "mult": 1.28},
        {"month": 7,  "name": "Prime Day",          "cats": ["Amazon Games", "Home Improvement", "Kitchen & Dining"], "mult": 1.45},
        {"month": 8,  "name": "Back to School",     "cats": ["Amazon Games", "Toys & Baby", "Fashion"], "mult": 1.28},
        {"month": 10, "name": "Pre-Black Friday",    "cats": ["Amazon Games","Home Improvement","Kitchen & Dining","Toys & Baby","Fashion"], "mult": 1.15},
        {"month": 11, "name": "Black Friday + 11/11", "cats": ["Amazon Games","Luxury Beauty","Fashion","Kitchen & Dining","Toys & Baby","Sports & Outdoors","Automotive","Home Improvement","Pet Supplies"], "mult": 1.6},
        {"month": 12, "name": "Christmas + 12/12",  "cats": ["Amazon Games","Luxury Beauty","Fashion","Kitchen & Dining","Toys & Baby","Sports & Outdoors","Home Improvement"], "mult": 1.45},
    ]

    def get_month_boost(self, month: int = None) -> dict[str, float]:
        """
        Combina SEASONAL_BOOST base con ciclo real de Amazon y eventos específicos.
        Retorna multiplicador refinado por categoría para el mes actual.
        """
        month = month or datetime.now().month
        base  = SEASONAL_BOOST.get(month, {})
        conv  = self.CONVERSION_INDEX.get(month, 70) / 70.0  # normalizar a 1.0

        # Boost base refinado con conversion index
        boost = {}
        for cat in AMAZON_COMMISSION:
            b = base.get(cat, 1.0)
            boost[cat] = round(b * conv, 3)

        # Aplicar eventos del mes
        for ev in self.EVENTS:
            if ev["month"] == month:
                for cat in ev["cats"]:
                    if cat in boost:
                        boost[cat] = round(boost[cat] * ev["mult"], 3)
                    else:
                        boost[cat] = round(ev["mult"], 3)
                print(f"  [Seasonality] {ev['name']}: ×{ev['mult']} en {len(ev['cats'])} cats")

        return boost

    def quarter_context(self) -> str:
        """Contexto del trimestre actual para logging."""
        month = datetime.now().month
        q = (month - 1) // 3 + 1
        share = self.AMAZON_QUARTERLY_SHARE.get(f"Q{q}", 0.235)
        return f"Q{q} ({share*100:.0f}% del revenue Amazon anual)"


# ══════════════════════════════════════════════════════════════════════════════
# ORQUESTADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class MacroRadar:
    """
    Combina todas las fuentes macro y produce una cola priorizada de keywords.

    Score final por keyword:
      score = trend_score × macro_boost × seasonal_boost × commission_weight

    donde:
      trend_score     = 0–100 (de Google Trends)
      macro_boost     = multiplicador de FRED/BanRep/Eurostat (0.8–1.5)
      seasonal_boost  = multiplicador estacional (1.0–1.8)
      commission_weight = comisión/10 (normaliza al 0–2 range)
    """

    def __init__(self):
        self.gtrends     = GTrendsSource()   # pytrends legacy (puede fallar post-Apr2025)
        self.gtrends_rss = GTrendsRSSSource()             # RSS oficial Google Trends
        self.rf_best     = RainforestBestsellersSource()  # Amazon bestsellers
        self.fred        = FREDSource()
        self.banrep      = BanRepSource()
        self.eurostat    = EurostatSource()
        self.ecommerce   = EcommerceSeasonality()

    def run(self, markets: list[str] = None, top_n: int = 30) -> list[MacroKeyword]:
        markets = markets or ["us", "es", "mx", "co"]
        print(f"\n{'═'*60}")
        print(f"  MACRO RADAR — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  Mercados: {', '.join(markets).upper()}")
        print(f"  Ciclo e-commerce: {self.ecommerce.quarter_context()}")
        print(f"{'═'*60}")

        # ── Fase 1a: Google Trends RSS (fuente primaria — sin librería) ────
        print("\n  [1a/5] Google Trends RSS — trending hoy (sin pytrends)")
        rss_trending = self.gtrends_rss.trending_now(markets)
        print(f"  → {len(rss_trending)} keywords desde RSS")

        # ── Fase 1b: Amazon Bestsellers vía Rainforest (señal de VENTAS) ──
        print("\n  [1b/5] Amazon Bestsellers — top productos por categoría")
        rf_trending = self.rf_best.get_bestsellers(max_calls=2)
        print(f"  → {len(rf_trending)} keywords desde Rainforest Bestsellers")

        # ── Fase 1c: pytrends legacy (fallback — puede fallar con HTTP 429) ─
        print("\n  [1c/5] Google Trends pytrends — seeds por categoría (fallback)")
        try:
            pt_trending = self.gtrends.trending_now(markets)
            print(f"  → {len(pt_trending)} keywords desde pytrends seeds")
        except Exception as e:
            print(f"  [pytrends] Error global: {e} — usando solo RSS + Rainforest")
            pt_trending = []

        # Merge con deduplicación — prioridad: RSS > Rainforest > pytrends
        seen_kws: dict[str, MacroKeyword] = {}
        for kw in (rss_trending + rf_trending + pt_trending):
            if kw.keyword not in seen_kws:
                seen_kws[kw.keyword] = kw
        trending = list(seen_kws.values())
        print(f"\n  Total keywords únicos: {len(trending)} "
              f"(RSS:{len(rss_trending)} + RF:{len(rf_trending)} + PT:{len(pt_trending)})")

        # ── Fase 2: Boost FRED (si hay key) ───────────────────────────────
        print(f"\n  [2/5] FRED — señales macro US {'✓ key OK' if FRED_KEY else '✗ sin key'}")
        fred_boost = self.fred.macro_boost() if FRED_KEY else {}
        if not fred_boost:
            print("  [FRED] Sin key — boost neutro")

        # ── Fase 3: BanRep (si hay mercado CO) ────────────────────────────
        banrep_boost = {}
        if "co" in markets:
            print("\n  [3/5] BanRep — señales macro Colombia (endpoint Suameca)")
            trm = self.banrep.trm()
            ipc_sig = self.banrep.ipc()
            tpm_sig = self.banrep.tpm()
            icc = self.banrep.confidence_index()
            if trm:     print(f"  [BanRep] {trm.note}")
            if ipc_sig: print(f"  [BanRep] {ipc_sig.note}")
            if tpm_sig: print(f"  [BanRep] {tpm_sig.note}")
            if icc:     print(f"  [BanRep] {icc.note}")
            banrep_boost = self.banrep.macro_boost_co(icc, trm, ipc_sig, tpm_sig)
        else:
            print("\n  [3/5] BanRep — saltado (CO no activo)")

        # ── Fase 4: Eurostat (si hay mercados EU) ─────────────────────────
        eu_markets  = [m.upper() for m in markets if m in ["es","de","fr","it","gb"]]
        eurostat_signals = []
        if eu_markets:
            print(f"\n  [4/5] Eurostat — confianza EU ({', '.join(eu_markets)})")
            eurostat_signals = self.eurostat.consumer_confidence(eu_markets)
            retail_sigs = self.eurostat.retail_sales(eu_markets[:3])
            eurostat_signals.extend(retail_sigs)
        else:
            print("\n  [4/5] Eurostat — saltado (no hay mercados EU activos)")

        eu_boost = self.eurostat.macro_boost_eu(eurostat_signals)

        # ── Fase 5: Estacionalidad e-commerce refinada ────────────────────
        print(f"\n  [5/5] E-commerce seasonality (Amazon 10-K + Prime Day + 11/11)")
        month   = datetime.now().month
        seasonal = self.ecommerce.get_month_boost(month)

        # ── Combinar scores ────────────────────────────────────────────────
        print(f"\n  Calculando scores ({len(trending)} trending keywords)...")
        scored: list[MacroKeyword] = []

        for kw in trending:
            cat = kw.category
            com = kw.commission
            ts  = kw.trend_score

            # Boost macro compuesto
            mb = 1.0
            if fred_boost:
                mb *= fred_boost.get(cat, 1.0)
            if banrep_boost and any(r.lower() == "co" for r in kw.regions):
                mb *= banrep_boost.get(cat, 1.0)
            for eu_reg in kw.regions:
                if eu_reg in eu_boost:
                    mb *= eu_boost[eu_reg].get(cat, 1.0)

            # Boost estacional refinado (ecommerce cycles)
            sb = seasonal.get(cat, 1.0)

            # Commission weight
            cw = 1.0 + (com / 20.0)

            raw   = ts * mb * sb * cw
            score = min(100.0, round(raw, 1))

            kw.macro_boost    = round(mb, 3)
            kw.seasonal_boost = round(sb, 2)
            kw.macro_score    = score
            scored.append(kw)

        scored.sort(key=lambda x: x.macro_score, reverse=True)
        top = scored[:top_n]

        # ── Mostrar y guardar ──────────────────────────────────────────────
        print(f"\n  TOP {min(top_n, len(top))} KEYWORDS MACRO:\n")
        for i, kw in enumerate(top, 1):
            print(f"  {i:>2}. [{kw.macro_score:.0f}] {kw.keyword:<30} "
                  f"{kw.category:<22} {kw.commission}%  "
                  f"× macro{kw.macro_boost:.2f} × seas{kw.seasonal_boost:.1f}")

        self._save_queue(top)
        return top

    def run_offline(self, markets: list[str] = None, top_n: int = 50) -> list[MacroKeyword]:
        """
        Modo offline/fallback — genera leads desde CATEGORY_SEEDS + RSS + Rainforest caché.
        Se activa cuando pytrends falla totalmente. Usa macro signals como score proxy.
        """
        markets = markets or ["us", "es", "mx", "co"]
        print(f"\n{'═'*60}")
        print(f"  MACRO RADAR (OFFLINE) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  Mercados: {', '.join(markets).upper()}")
        print(f"  Ciclo: {self.ecommerce.quarter_context()}")
        print(f"{'═'*60}")

        # Intentar RSS primero (no requiere nada externo)
        print("\n  Intentando Google Trends RSS...")
        rss_kws = self.gtrends_rss.trending_now(markets)
        if rss_kws:
            print(f"  RSS disponible: {len(rss_kws)} keywords")

        # Rainforest bestsellers desde caché (no gasta API calls)
        rf_kws = self.rf_best.get_bestsellers(max_calls=1)

        # Macro signals
        print("\n  Cargando señales macro...")
        fred_boost = self.fred.macro_boost() if FRED_KEY else {}

        banrep_boost = {}
        ipc_sig = tpm_sig = trm_sig = None
        if "co" in markets:
            trm_sig = self.banrep.trm()
            ipc_sig = self.banrep.ipc()
            tpm_sig = self.banrep.tpm()
            icc     = self.banrep.confidence_index()
            if trm_sig: print(f"  [BanRep] {trm_sig.note}")
            if ipc_sig: print(f"  [BanRep] {ipc_sig.note}")
            if tpm_sig: print(f"  [BanRep] {tpm_sig.note}")
            banrep_boost = self.banrep.macro_boost_co(icc, trm_sig, ipc_sig, tpm_sig)

        eu_markets = [m.upper() for m in markets if m in ["es","de","fr","it","gb"]]
        eu_boost   = {}
        if eu_markets:
            retail_sigs = self.eurostat.retail_sales(eu_markets[:3])
            eu_boost    = self.eurostat.macro_boost_eu(
                self.eurostat.consumer_confidence(eu_markets) + retail_sigs
            )

        month    = datetime.now().month
        seasonal = self.ecommerce.get_month_boost(month)

        # Score base por mes (conversion index normalizado)
        conv_base = self.ecommerce.CONVERSION_INDEX.get(month, 70)

        # Generar leads desde CATEGORY_SEEDS
        n_seeds = sum(len(v) for v in GTrendsSource.CATEGORY_SEEDS.values())
        print(f"\n  Generando leads desde {n_seeds} seeds + {len(rss_kws)} RSS + {len(rf_kws)} RF...\n")
        keywords: list[MacroKeyword] = []
        seen: set[str] = set()
        geo  = markets[0].upper()

        # Seeds base
        for cat, seeds in GTrendsSource.CATEGORY_SEEDS.items():
            com = AMAZON_COMMISSION.get(cat, 3.0)
            for seed in seeds:
                if seed in seen:
                    continue
                seen.add(seed)
                ts = min(100.0, conv_base * 0.9 + hash(seed) % 15)
                mb = 1.0
                if fred_boost:   mb *= fred_boost.get(cat, 1.0)
                if banrep_boost: mb *= banrep_boost.get(cat, 1.0)
                for eu_reg, eu_b in eu_boost.items():
                    mb *= eu_b.get(cat, 1.0) ** 0.3
                sb = seasonal.get(cat, 1.0)
                cw = 1.0 + (com / 20.0)
                score = min(100.0, round(ts * mb * sb * cw, 1))
                keywords.append(MacroKeyword(
                    keyword=seed, category=cat, commission=com,
                    macro_score=score, trend_score=ts,
                    macro_boost=round(mb, 3),
                    seasonal_boost=round(sb, 2),
                    regions=[geo],
                    source="macro_offline",
                ))

        # Añadir RSS y Rainforest con el mismo pipeline de boost
        for kw in (rss_kws + rf_kws):
            if kw.keyword in seen:
                continue
            seen.add(kw.keyword)
            cat = kw.category
            com = kw.commission
            ts  = kw.trend_score
            mb  = 1.0
            if fred_boost:   mb *= fred_boost.get(cat, 1.0)
            if banrep_boost: mb *= banrep_boost.get(cat, 1.0)
            sb = seasonal.get(cat, 1.0)
            cw = 1.0 + (com / 20.0)
            kw.macro_boost    = round(mb, 3)
            kw.seasonal_boost = round(sb, 2)
            kw.macro_score    = min(100.0, round(ts * mb * sb * cw, 1))
            keywords.append(kw)

        keywords.sort(key=lambda x: x.macro_score, reverse=True)
        top = keywords[:top_n]

        print(f"  TOP {len(top)} KEYWORDS (macro offline):\n")
        for i, kw in enumerate(top, 1):
            src_tag = f"[{kw.source[:8]}]" if kw.source != "macro_offline" else ""
            print(f"  {i:>2}. [{kw.macro_score:.0f}] {kw.keyword:<35} "
                  f"{kw.category:<22} {kw.commission}%  "
                  f"× macro{kw.macro_boost:.2f} × seas{kw.seasonal_boost:.1f} {src_tag}")

        self._save_queue(top)
        return top

    def _save_queue(self, keywords: list[MacroKeyword]):
        """Guarda la cola en JSON y también la añade a leads.csv."""
        data = {
            "generated": datetime.now().isoformat(),
            "keywords":  [asdict(kw) for kw in keywords],
        }
        MACRO_QUEUE_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n  Cola guardada en {MACRO_QUEUE_FILE}")
        self._append_to_leads(keywords)

    def _append_to_leads(self, keywords: list[MacroKeyword]):
        """Añade keywords macro al leads.csv para que el orchestrator los procese."""
        import csv
        leads_path = Path("leads.csv")
        existe = leads_path.exists()

        with leads_path.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "subreddit","amazon_cat","comision_pct","keyword",
                "hits_max","hits_reciente","slope","trending","titulo","url"
            ])
            if not existe:
                w.writeheader()
            escritos, descartados = 0, 0
            for kw in keywords:
                if not es_keyword_producto(kw.keyword):
                    print(f"  [skip] '{kw.keyword}' no parece un producto buscable")
                    descartados += 1
                    continue
                row = kw.to_lead_row()
                w.writerow({
                    "subreddit":    row["subreddit"],
                    "amazon_cat":   row["amazon_cat"],
                    "comision_pct": row["comision_pct"],
                    "keyword":      row["keyword"],
                    "hits_max":     row["hits_max"],
                    "hits_reciente":row["hits_reciente"],
                    "slope":        row["slope"],
                    "trending":     row["trending"],
                    "titulo":       row["titulo"],
                    "url":          row["url"],
                })
                escritos += 1
        print(f"  {escritos} keywords añadidos a leads.csv"
              + (f" ({descartados} descartados por no parecer producto)" if descartados else ""))


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TrendVortex — Macro Radar")
    parser.add_argument("--markets", default="us,es,mx,co")
    parser.add_argument("--top",     type=int, default=30)
    parser.add_argument("--source",  default="all",
                        choices=["all","trends","fred","banrep","eurostat"])
    args = parser.parse_args()

    markets = [m.strip() for m in args.markets.split(",") if m.strip()]
    radar   = MacroRadar()

    if args.source == "all":
        radar.run(markets=markets, top_n=args.top)
    elif args.source == "trends":
        kws = radar.gtrends.trending_now(markets)
        print(f"\n{len(kws)} keywords trending")
    elif args.source == "fred":
        boost = radar.fred.macro_boost()
        print("\nBoost por categoría:")
        for cat, b in sorted(boost.items(), key=lambda x: -x[1]):
            print(f"  {cat:<25} × {b:.2f}")
    elif args.source == "banrep":
        icc = radar.banrep.confidence_index()
        trm = radar.banrep.trm()
        if icc: print(f"  ICC Colombia: {icc.value:.1f} ({icc.note})")
        if trm: print(f"  TRM: {trm.note}")
    elif args.source == "eurostat":
        sigs = radar.eurostat.consumer_confidence()
        for s in sigs:
            print(f"  {s.region}: {s.value:.1f} ({s.note})")
