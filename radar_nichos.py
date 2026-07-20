# -*- coding: utf-8 -*-
"""
radar_nichos.py — Fase 1: Extractor de Tendencias
  - Reddit RSS  → detecta buying-intent posts (EN + ES)
  - pytrends    → valida keyword subiendo (hits>=70 o slope>10)
  - Telegram    → alerta con score, categoría Amazon y enlace

Uso:
  python radar_nichos.py          # un ciclo completo
  python radar_nichos.py --loop   # loop cada 3 horas
"""

import sys, os, re, time, csv
import feedparser, requests
from pathlib import Path
from dotenv import load_dotenv

from keyword_filter import extraer_keyword, es_keyword_producto as _es_keyword_producto

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

# ── Patch urllib3 >= 2.0 vs pytrends incompatibilidad ────────────────────────
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

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEEN_FILE   = Path("seen_ids.txt")
LEADS_FILE  = Path("leads.csv")
INTERVALO_H = 3

# ══════════════════════════════════════════════════════════════════════════════
# SUBREDDITS — priorizados por categorías con comisión Amazon >=3%
# ══════════════════════════════════════════════════════════════════════════════
SUBREDDITS = [
    # Kitchen & Dining (4.5%) — mejor comisión en físicos
    "Cooking", "sousvide", "coffee", "grilling", "instantpot",
    "KitchenConfidential", "cookware",
    # Automotive (4.5%)
    "AutoDetailing", "MechanicalAdvice", "cars", "CarAV",
    # Luxury Beauty (10%) — el jackpot
    "SkincareAddiction", "MakeupAddiction", "HaircareScience",
    # Fashion / Shoes / Watches (4%)
    "malefashionadvice", "femalefashionadvice", "Watches", "frugalmalefashion",
    # Sports & Outdoors (3%)
    "camping", "hiking", "running", "cycling", "fitness", "homegym",
    # Toys & Baby (3%)
    "Parenting", "beyondthebump", "toddlers",
    # Amazon Games / Peripherals (20% en software)
    "MechanicalKeyboards", "MouseReview", "buildapc", "pcgaming",
    # Home Organization (Kitchen overlap 4.5%)
    "organization", "HomeImprovement", "DIY", "CleaningTips",
    # Compra directa — alta intención
    "BuyItForLife", "shutupandtakemymoney", "Frugal", "Deals",
    "onebag", "minimalism",
    # Mascotas — categoría propia Amazon 3-5%
    "cats", "dogs", "petadvice", "CatAdvice",
    # Hispanohablantes — baja competencia SEO
    "mexico", "colombia", "argentina", "chile", "spain",
    "es", "latinoamerica", "Frugal_es",
]

# ══════════════════════════════════════════════════════════════════════════════
# CATEGORÍA AMAZON por subreddit — para mostrar en alerta y filtrar
# ══════════════════════════════════════════════════════════════════════════════
AMAZON_CATEGORY = {
    "Cooking": ("Kitchen & Dining", 4.5),
    "sousvide": ("Kitchen & Dining", 4.5),
    "coffee": ("Kitchen & Dining", 4.5),
    "grilling": ("Kitchen & Dining", 4.5),
    "instantpot": ("Kitchen & Dining", 4.5),
    "KitchenConfidential": ("Kitchen & Dining", 4.5),
    "cookware": ("Kitchen & Dining", 4.5),
    "AutoDetailing": ("Automotive", 4.5),
    "MechanicalAdvice": ("Automotive", 4.5),
    "cars": ("Automotive", 4.5),
    "CarAV": ("Automotive", 4.5),
    "SkincareAddiction": ("Luxury Beauty", 10.0),
    "MakeupAddiction": ("Luxury Beauty", 10.0),
    "HaircareScience": ("Luxury Beauty", 10.0),
    "malefashionadvice": ("Fashion", 4.0),
    "femalefashionadvice": ("Fashion", 4.0),
    "Watches": ("Fashion", 4.0),
    "frugalmalefashion": ("Fashion", 4.0),
    "MechanicalKeyboards": ("Amazon Games", 20.0),
    "MouseReview": ("Amazon Games", 20.0),
    "buildapc": ("Amazon Games", 20.0),
    "pcgaming": ("Amazon Games", 20.0),
    "camping": ("Sports & Outdoors", 3.0),
    "hiking": ("Sports & Outdoors", 3.0),
    "running": ("Sports & Outdoors", 3.0),
    "cycling": ("Sports & Outdoors", 3.0),
    "fitness": ("Sports & Outdoors", 3.0),
    "homegym": ("Sports & Outdoors", 3.0),
    "cats": ("Pet Supplies", 5.0),
    "dogs": ("Pet Supplies", 5.0),
    "petadvice": ("Pet Supplies", 5.0),
    "CatAdvice": ("Pet Supplies", 5.0),
    "Parenting": ("Toys & Baby", 3.0),
    "beyondthebump": ("Toys & Baby", 3.0),
    "toddlers": ("Toys & Baby", 3.0),
}

def get_amazon_cat(subreddit):
    return AMAZON_CATEGORY.get(subreddit, ("General", 3.0))

# ══════════════════════════════════════════════════════════════════════════════
# PATRONES BUYING INTENT — inglés + español
# ══════════════════════════════════════════════════════════════════════════════
INTENT_EN = [
    r"alternative to\b", r"alternatives? (for|to)\b", r"replacement for\b",
    r"where (can i|to) (buy|find|get)\b", r"best place to buy\b",
    r"best budget\b", r"best (cheap|affordable)\b", r"under \$\d+",
    r"recommend(ation)?s? (for|me|a)\b", r"suggest(ion)?s?\b",
    r"looking for (a |an )?(good|best|cheap|affordable)?\b",
    r"is there (a |an )?product\b", r"is there (a |an )?tool\b",
    r"what do you (use|recommend)\b", r"what('s| is) (the best|a good)\b",
    r"tired of\b", r"frustrated (with|by)\b", r"wish there was\b",
    r"worth (it|every penny|the price)\b", r"just bought\b",
    r"finally got\b", r"upgraded (my|to)\b", r"need (a |an )?(good|better)?\b",
    r"anyone know (a |an |where)\b", r"help me (find|choose|pick)\b",
    r"which (one|brand) (should|do) (i|you)\b",
]
INTENT_ES = [
    r"alternativa (a|para)\b", r"alternativas? (a|para)\b",
    r"d[oó]nde (comprar|conseguir|encontrar)\b",
    r"mejor (opci[oó]n|producto|marca) para\b",
    r"recomiendan (algo|alguno|una)\b", r"recomienden\b",
    r"busco (algo|una|un|el mejor)\b", r"necesito (recomendar|sugerir|algo)\b",
    r"vale la pena\b", r"merece la pena\b",
    r"qu[eé] (marca|producto|opci[oó]n) (usan|recomiendan|es mejor)\b",
    r"cansado de\b", r"harto de\b", r"ojalá (hubiera|existiera)\b",
    r"acabo de comprar\b", r"reci[eé]n compr[eé]\b",
    r"cu[aá]l (es el mejor|compro|eligen)\b",
    r"ayuda para (elegir|escoger|comprar)\b",
    r"me pueden recomendar\b", r"alguno conoce\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in INTENT_EN + INTENT_ES]

def tiene_intent(texto: str) -> str | None:
    for pat in _COMPILED:
        m = pat.search(texto)
        if m:
            return m.group(0)
    return None

# ══════════════════════════════════════════════════════════════════════════════
# EXTRACCIÓN DE KEYWORD — ver keyword_filter.py (compartido con macro_radar.py
# y orchestrator.py, para que ningún keyword de queja/troubleshooting se cuele
# sin importar por cuál de los dos radares haya entrado).
# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE TRENDS — validación con pytrends
# ══════════════════════════════════════════════════════════════════════════════
_trends_cache: dict[str, dict] = {}

def validar_trends(keyword: str) -> dict | None:
    if keyword in _trends_cache:
        print(f"  [Trends] Cache hit: '{keyword}'")
        return _trends_cache[keyword]
    try:
        from pytrends.request import TrendReq
        time.sleep(35)   # 35s base — suficiente para evitar 429 en uso normal
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 30),
                      retries=3, backoff_factor=2.0)
        pt.build_payload([keyword], timeframe="today 3-m", geo="US")
        df = pt.interest_over_time()
        if df is None or df.empty or keyword not in df.columns:
            return None
        serie = df[keyword].tolist()
        if len(serie) < 8:
            return None
        hits_max      = max(serie)
        hits_reciente = round(sum(serie[-4:]) / 4, 1)
        hits_previo   = round(sum(serie[-12:-4]) / 8, 1)
        slope         = round(hits_reciente - hits_previo, 1)
        result = {
            "hits_max":      hits_max,
            "hits_reciente": hits_reciente,
            "slope":         slope,
            "trending":      hits_reciente >= 70 or slope > 10,
        }
        _trends_cache[keyword] = result
        return result
    except Exception as e:
        err = str(e)
        if "429" in err or "Too Many" in err:
            # Bloqueado — esperar 3 minutos antes de continuar
            print(f"  [Trends] 429 detectado — pausa 3 min...")
            time.sleep(180)
        else:
            print(f"  [Trends] Error '{keyword}': {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
def _telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"  [Telegram] Error: {e}")

def _alerta_nicho(subreddit, titulo, url, intent, keyword, trends, amazon_cat, comision):
    trend_emoji = "📈" if trends["trending"] else "📊"
    msg = (
        f"🎯 <b>NICHO — r/{subreddit}</b>\n\n"
        f"<b>Keyword:</b> {keyword}\n"
        f"<b>Categoria Amazon:</b> {amazon_cat} ({comision}% comision)\n"
        f"<b>Intent:</b> <i>{intent}</i>\n\n"
        f"{trend_emoji} <b>Google Trends (US 3m)</b>\n"
        f"  Pico: {trends['hits_max']}/100 | "
        f"Reciente: {trends['hits_reciente']}/100 | "
        f"Slope: {trends['slope']:+}\n\n"
        f"<b>Post:</b> {titulo[:180]}\n"
        f"<b>Link:</b> {url}"
    )
    _telegram(msg)

# ══════════════════════════════════════════════════════════════════════════════
# SEEN IDS + LEADS CSV
# ══════════════════════════════════════════════════════════════════════════════
def _cargar_seen():
    if SEEN_FILE.exists():
        return set(SEEN_FILE.read_text(encoding="utf-8").splitlines())
    return set()

def _guardar_seen(pid: str):
    with SEEN_FILE.open("a", encoding="utf-8") as f:
        f.write(pid + "\n")

def _guardar_lead(subreddit, titulo, url, keyword, trends, amazon_cat, comision):
    existe = LEADS_FILE.exists()
    with LEADS_FILE.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if not existe:
            w.writerow(["subreddit", "amazon_cat", "comision_pct", "keyword",
                        "hits_max", "hits_reciente", "slope", "trending",
                        "titulo", "url"])
        w.writerow([subreddit, amazon_cat, comision, keyword,
                    trends["hits_max"], trends["hits_reciente"],
                    trends["slope"], trends["trending"],
                    titulo[:120], url])

# ══════════════════════════════════════════════════════════════════════════════
# ESCANEO
# ══════════════════════════════════════════════════════════════════════════════
def escanear_subreddit(subreddit: str, seen: set) -> int:
    url = f"https://www.reddit.com/r/{subreddit}/new/.rss"
    encontrados = 0
    amazon_cat, comision = get_amazon_cat(subreddit)
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            post_id = entry.get("id", entry.get("link", ""))
            if post_id in seen:
                continue
            titulo = entry.get("title", "")
            texto  = titulo + " " + entry.get("summary", "")

            intent = tiene_intent(texto)
            if not intent:
                continue

            keyword = extraer_keyword(titulo, intent)

            # Filtro pre-Trends: descartar keywords que claramente no son productos
            if not _es_keyword_producto(keyword):
                continue

            print(f"  [Trends] '{keyword}' ({amazon_cat} {comision}%)")
            trends = validar_trends(keyword)

            if trends is None:
                continue
            if not trends["trending"] and trends["slope"] <= 5:
                print(f"  [skip] slope={trends['slope']:+} reciente={trends['hits_reciente']}")
                continue

            seen.add(post_id)
            _guardar_seen(post_id)
            link = entry.get("link", "")

            print(f"  NICHO [{comision}%] '{keyword}' | "
                  f"hits={trends['hits_reciente']} slope={trends['slope']:+}")
            print(f"  {link}")

            _alerta_nicho(subreddit, titulo, link, intent, keyword,
                          trends, amazon_cat, comision)
            _guardar_lead(subreddit, titulo, link, keyword, trends,
                          amazon_cat, comision)
            encontrados += 1
            break
    except Exception as e:
        print(f"  [Error] r/{subreddit}: {e}")
    return encontrados

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def run_ciclo(ciclo_num: int):
    seen = _cargar_seen()
    print(f"\n{'='*55}")
    print(f"  CICLO #{ciclo_num} — {len(SUBREDDITS)} subreddits")
    print(f"{'='*55}")
    total = 0
    for sub in SUBREDDITS:
        n = escanear_subreddit(sub, seen)
        total += n
        time.sleep(1.5)
    print(f"\n  Ciclo #{ciclo_num} — {total} nichos validados")
    return total

if __name__ == "__main__":
    import sys as _sys
    modo_loop = "--loop" in _sys.argv
    print("Radar de Nichos — Fase 1")
    print(f"  Subreddits : {len(SUBREDDITS)}")
    print(f"  Modo       : {'loop cada ' + str(INTERVALO_H) + 'h' if modo_loop else 'un ciclo'}")
    print(f"  Telegram   : {'configurado' if TELEGRAM_TOKEN else 'sin configurar (.env)'}\n")
    ciclo = 1
    while True:
        run_ciclo(ciclo)
        if not modo_loop:
            break
        print(f"\n  Proximo ciclo en {INTERVALO_H}h...")
        time.sleep(INTERVALO_H * 3600)
        ciclo += 1
