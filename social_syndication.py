# -*- coding: utf-8 -*-
"""
social_syndication.py — Copys persuasivos (Facebook, X, LinkedIn, Pinterest)
para las páginas de TrendVortex que YA están confirmadas como indexadas en
Google. Reddit queda aparte: ya lo cubre reddit_comment_bot.py (necesita un
hilo real donde comentar, no un post proactivo).

Objetivo: derivar tráfico social hacia esas URLs puntuales (no páginas nuevas)
para reforzar señales de autoridad/engagement en el dominio mientras el
throttling de publicación (ver orchestrator.py) baja la velocidad de creación.
Plan a 90 días: 1 página/día rotando por prioridad, entregada a Telegram —
vos elegís 1-2 redes por día, nunca las 4 el mismo día para el mismo producto
(postear el mismo texto en todos lados a la vez también se ve como bot).

Este script NO publica nada — solo lee los HTML ya generados en docs/<slug>/
(cero llamadas a Amazon/eBay/Claude) y arma el texto. Si GEMINI_API_KEY está
configurada en .env, la usa para variar la redacción (mismo patrón que
reddit_comment_bot.py); si no, cae a las plantillas locales sin costo.

Flujo diario automático (hilo en main.py → send_daily_batch): 1 página
indexada/día por prioridad → kit guerrilla (Reddit + Facebook Groups, 5
variaciones c/u) → 2 mensajes a Telegram, listos para copiar y pegar.
FB/X/LinkedIn/Pinterest (build_copies/run) siguen disponibles vía CLI para
export manual, pero ya no son lo que se envía automático por día.

Uso:
  python social_syndication.py --rank                  # ranking de prioridad de las páginas indexadas
  python social_syndication.py --preview best-baby-monitor   # ver el kit guerrilla sin gastar el turno del día
  python social_syndication.py --daily                 # dispara manualmente el envío diario a Telegram
  python social_syndication.py                         # export masivo FB/X/LinkedIn/Pinterest → social_copies/YYYY-MM-DD.md
  python social_syndication.py --limit 5 --platform pinterest --out mis_copys.md
"""
from __future__ import annotations
import argparse
import html
import json
import math
import random
import re
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR       = Path("docs")
STATUS_FILE    = Path("indexing_status.json")
SITE_URL       = "https://trendvortex.tech"
OUT_DIR        = Path("social_copies")
ROTATION_FILE  = Path("social_rotation_state.json")

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")


# ── Extracción de datos desde el HTML ya publicado ────────────────────────────

def _clean(text: str | None) -> str | None:
    if not text:
        return None
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def extract_page_data(slug: str) -> dict | None:
    path = DOCS_DIR / slug / "index.html"
    if not path.exists():
        return None
    page_html = path.read_text(encoding="utf-8", errors="ignore")

    data = {
        "slug": slug,
        "url": f"{SITE_URL}/{slug}/",
        "title": None, "name": None, "image": None, "price": None,
        "rating": None, "reviews": None, "features": [], "description": None,
    }

    m = re.search(r"<title>([^<]+)</title>", page_html)
    if m:
        title = _clean(m.group(1))
        title = re.sub(r"\s*[\|—-]\s*TrendVortex.*$", "", title or "").strip()
        data["title"] = title or None

    m = re.search(r'name="description"\s+content="([^"]+)"', page_html)
    if m:
        data["description"] = _clean(m.group(1))

    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page_html, re.S):
        try:
            obj = json.loads(block)
        except Exception:
            continue
        if obj.get("@type") == "Product":
            data["name"]  = _clean(obj.get("name"))
            data["image"] = obj.get("image")
            offers = obj.get("offers") or {}
            data["price"] = offers.get("price")
            rating = obj.get("aggregateRating") or {}
            data["rating"]  = rating.get("ratingValue")
            data["reviews"] = rating.get("reviewCount")
            if not data["description"]:
                data["description"] = _clean(obj.get("description"))
            break  # primer Product — suficiente (páginas "vs" pueden traer varios)

    if not data["image"]:
        m = re.search(r'<img[^>]+src="([^"]+)"', page_html)
        if m:
            data["image"] = m.group(1)

    pros_match = re.search(r'pros-box.*?<ul[^>]*>(.*?)</ul>', page_html, re.S)
    if pros_match:
        items = re.findall(r"<li[^>]*>(.*?)</li>", pros_match.group(1), re.S)
        data["features"] = [_clean(re.sub(r"<[^<]+?>", "", i)) for i in items][:4]
        data["features"] = [f for f in data["features"] if f]

    if not data["name"]:
        data["name"] = data["title"] or slug.replace("-", " ").replace("best ", "", 1).title()

    return data


def indexed_slugs() -> list[str]:
    if not STATUS_FILE.exists():
        return []
    status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return sorted(s for s, v in status.items() if v.get("status") == "indexed")


# ── Priorización — qué página empujar primero ─────────────────────────────────
# Score = rating × log(reviews+1): premia producto con buena prueba social
# (más fácil de convertir el clic social en venta), no solo tráfico. Páginas
# sin rating/precio (hubs tipo "best-beauty") reciben un baseline modesto —
# igual sirven para tráfico, solo van después en la cola.

def priority_score(data: dict) -> float:
    try:
        rating  = float(data.get("rating") or 0)
        reviews = int(float(data.get("reviews") or 0))
    except (TypeError, ValueError):
        rating, reviews = 0.0, 0
    if rating <= 0:
        return 0.5
    return rating * math.log(reviews + 1, 10)


def ranked_indexed_pages() -> list[tuple[str, float, dict]]:
    """Todas las páginas indexadas, de mayor a menor prioridad de empuje social."""
    scored: list[tuple[str, float, dict]] = []
    for slug in indexed_slugs():
        data = extract_page_data(slug)
        if data is None:
            continue
        scored.append((slug, priority_score(data), data))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ── Hashtags por categoría (heurística por palabras clave, sin llamadas API) ──

STOPWORDS = {"best", "for", "in", "of", "the", "a", "an", "and", "with", "to",
             "2026", "2025", "vs"}

CATEGORY_MAP: list[dict] = [
    {"match": ["baby monitor", "stroller", "toddler", "baby product"],
     "hashtags": ["#BabyGear", "#NewMomFinds", "#ParentingHacks"],
     "fb_groups_es": ["Mamás primerizas / crianza", "Compra-venta de artículos para bebés", "Ofertas y outlet de bebés"],
     "fb_groups_en": ["New moms / parenting groups", "Baby gear buy & sell", "Baby deals & discounts"]},
    {"match": ["skin care", "skincare", "serum", "sunscreen", "spf", "tanning", "beauty", "makeup", "chanel"],
     "hashtags": ["#SkincareRoutine", "#BeautyFinds", "#GlowUp"],
     "fb_groups_es": ["Rutina de skincare / K-beauty", "Compra-venta de maquillaje y belleza", "Ofertas de belleza y cuidado personal"],
     "fb_groups_en": ["Skincare routine / K-beauty", "Makeup & beauty buy-sell", "Beauty deals & personal care"]},
    {"match": ["gaming monitor", "gaming mouse", "mechanical keyboard", "keyboard", "gaming"],
     "hashtags": ["#GamingSetup", "#PCGaming", "#TechFinds"],
     "fb_groups_es": ["Setup gamer / PC master race", "Compra-venta de periféricos gamer", "Comunidad de gamers (país/región)"],
     "fb_groups_en": ["PC gaming setups / battlestations", "Gaming peripherals buy & sell", "Local gamer community"]},
    {"match": ["camping", "paddle board", "tent", "beach", "sun hat", "sun shade", "uv protection"],
     "hashtags": ["#OutdoorGear", "#AdventureReady", "#SummerVibes"],
     "fb_groups_es": ["Camping y outdoor", "Compra-venta de equipo deportivo/aventura", "Amantes de la playa y el sol"],
     "fb_groups_en": ["Camping & outdoor gear", "Sports/adventure gear buy & sell", "Beach & summer lovers"]},
    {"match": ["robot vacuum", "air fryer", "roomba", "roborock"],
     "hashtags": ["#SmartHome", "#HomeFinds", "#KitchenGadgets"],
     "fb_groups_es": ["Hogar inteligente / smart home", "Ofertas de electrodomésticos", "Trucos y organización del hogar"],
     "fb_groups_en": ["Smart home enthusiasts", "Appliance deals", "Home organization hacks"]},
    {"match": ["running", "sneakers", "earrings", "dress", "straw hat"],
     "hashtags": ["#FashionFinds", "#StyleInspo", "#OOTD"],
     "fb_groups_es": ["Moda y estilo personal", "Compra-venta de ropa y accesorios", "Runners / vida fitness"],
     "fb_groups_en": ["Fashion & personal style", "Clothing & accessories buy-sell", "Runners / fitness lifestyle"]},
    {"match": ["pet cooling", "tri-tip", "steak"],
     "hashtags": ["#PetCare", "#HomeFinds"],
     "fb_groups_es": ["Dueños de mascotas", "Cuidado y bienestar animal", "Ofertas para mascotas"],
     "fb_groups_en": ["Pet owners", "Animal care & wellness", "Pet deals"]},
]

GENERIC_TAGS = ["#AmazonFinds", "#TrendVortex", "#ShopSmart", "#DealsOfTheDay", "#MustHave2026"]
GENERIC_FB_GROUPS_ES = ["Ofertas y cupones online", "Comunidad de compradores / recomendaciones de productos",
                        "Grupo de reventa/marketplace local"]
GENERIC_FB_GROUPS_EN = ["Online deals & coupons", "Product recommendations community",
                        "Local marketplace/resale group"]


def _match_category(keyword: str) -> dict | None:
    kw_lower = keyword.lower()
    for cat in CATEGORY_MAP:
        if any(k in kw_lower for k in cat["match"]):
            return cat
    return None


def build_hashtags(keyword: str, n: int = 5) -> list[str]:
    cat = _match_category(keyword)
    tags: list[str] = list(cat["hashtags"]) if cat else []

    words = [w for w in re.findall(r"[A-Za-z']+", keyword) if w.lower() not in STOPWORDS]
    if words:
        tags.append("#" + "".join(w.capitalize() for w in words[:4]))

    tags.extend(GENERIC_TAGS)

    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:n]


# ── Detección de idioma del contenido original (título/descripción/features) ──
# Heurística liviana por palabras función, sin dependencias nuevas — sirve
# porque hoy el sitio es 100% inglés, pero deja listo el caso "es" si algún
# día se indexan páginas del mercado "es" (ver markets.py).

ES_MARKERS = {"el", "la", "los", "las", "de", "que", "para", "con", "una", "uno",
              "es", "son", "más", "cómo", "qué", "cuál", "mejor", "precio"}
EN_MARKERS = {"the", "and", "for", "with", "this", "that", "best", "is", "are",
              "how", "what", "which", "review", "price", "buy"}


def _detect_language(data: dict) -> str:
    text = " ".join(filter(None, [data.get("title"), data.get("description")]
                           + (data.get("features") or []))).lower()
    if re.search(r"[áéíóúñ¿¡]", text):
        return "es"
    words = re.findall(r"[a-z']+", text)
    es_score = sum(1 for w in words if w in ES_MARKERS)
    en_score = sum(1 for w in words if w in EN_MARKERS)
    return "es" if es_score > en_score else "en"


def build_fb_group_keywords(keyword: str, lang: str = "en", n: int = 3) -> list[str]:
    cat = _match_category(keyword)
    key = "fb_groups_es" if lang == "es" else "fb_groups_en"
    generic = GENERIC_FB_GROUPS_ES if lang == "es" else GENERIC_FB_GROUPS_EN
    groups = list(cat[key]) if cat else list(generic)
    return groups[:n]


def build_reddit_search_terms(keyword: str, lang: str = "en", n: int = 3) -> list[str]:
    # \w unicode-aware en str patterns: conserva acentos/ñ (ej. "bebé", no "beb")
    core = " ".join(w for w in re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?", keyword)
                     if w.lower() not in STOPWORDS).lower()
    core = core or keyword.lower()
    if lang == "es":
        terms = [
            f"qué {core} comprar reddit",
            f"recomendación {core} reddit",
            f"{core} vale la pena reddit",
        ]
    else:
        terms = [
            f"what {core} to buy reddit",
            f"best {core} recommendation reddit",
            f"is {core} worth it reddit",
        ]
    return terms[:n]


# ── Plantillas de copy por red ─────────────────────────────────────────────────

# Banco de "plantillas lógicas" ampliado (~8-10 por canal) — la variedad
# real evita la "regresión a la media" (todo termina sonando igual tras
# semanas de uso) que detectan los clasificadores anti-spam. Cada hook
# sigue un patrón distinto (problema/solución, error común, curiosidad,
# dato/estadística, análisis en pasos) en vez de ser la misma frase con
# sinónimos.
FB_HOOKS = [
    "😍 ¿Buscando {name} que realmente valga la pena en {year}?",
    "🔎 Antes de comprar {name}, mira esto:",
    "🙋 Me preguntaron mucho por {name} — acá el resumen honesto:",
    "🤔 ¿Te ha pasado que comprás {name} y no cumple lo que promete?",
    "📝 Nota rápida para quien esté evaluando {name}:",
    "😅 El error que casi cometo con {name} (y cómo lo evité):",
    "💬 Alguien me preguntó por {name} hoy, así que lo dejo por acá:",
    "🧐 Llevaba tiempo mirando opciones de {name}, esto fue lo que encontré:",
]
FB_CTA = [
    "👉 Reseña completa (pros, contras y dónde conseguirlo) en el link:",
    "👉 Toda la comparativa y el precio actual, acá:",
    "👉 Análisis completo antes de que se agote el stock:",
    "👉 Lo bueno y lo no tan bueno, sin filtro, acá:",
]
FB_CLOSERS = [
    "¿Ustedes qué usan para esto? 👀",
    "¿Alguien más anduvo buscando lo mismo?",
    "¿Vale la pena para lo que necesitás vos?",
    "¿Qué tal les fue a ustedes con algo parecido?",
]

X_HOOKS = [
    "{emoji} {name} — ¿vale la pena?",
    "{emoji} Probamos/analizamos {name}:",
    "{emoji} 3 cosas que no sabías de {name}:",
    "{emoji} El dato que cambia todo sobre {name}:",
    "{emoji} {name} en números:",
    "{emoji} Lo que nadie te dice de {name}:",
]
X_CTA = ["Reseña completa 👇", "Todo el detalle acá 👇", "Link con el análisis 👇", "Análisis completo 👇"]

PIN_CTA = [
    "Mira la reseña completa, precio y alternativas 👉",
    "Toda la comparativa antes de comprar 👉",
    "Guía completa (pros, contras, precio) 👉",
]

# LinkedIn — tono "broetry" (una idea por línea, ROI/beneficio operativo
# primero, sin relleno) en vez de prosa corrida.
LI_HOOKS = [
    "Encontré algo interesante mientras investigaba {name}:",
    "Compartiendo un hallazgo — {name}:",
    "Un dato rápido sobre {name} para quien esté evaluando opciones:",
    "Lo que aprendí comparando opciones de {name}:",
    "Análisis rápido: dónde {name} sí justifica la inversión.",
    "El ROI real de {name}, en 3 puntos:",
]

EMOJIS = ["✨", "🔥", "💡", "🛒", "⭐"]

X_MAX_CHARS = 280

GEMINI_ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/models/"
                    "gemini-2.5-flash:generateContent")


# ── Variedad de redacción vía Gemini (opcional, mismo patrón que
#    reddit_comment_bot.py: si no hay GEMINI_API_KEY, no hace nada) ───────────

# Reglas de estilo por canal (patrones 2026 que reportan mejor alcance
# orgánico) — inyectadas en el prompt de reescritura para que la variedad
# de Gemini vaya en la dirección correcta, no solo "sonar más humano".
_PLATFORM_STYLE_RULES = {
    "X (Twitter)": (
        "Tone: concise analyst, not a hypeman. Zero or at most ONE hashtag "
        "total (extra hashtags read as spam and hurt reach). Lead with a "
        "concrete stat, number, or a surprising contradiction — never a "
        "generic opener. Hard limit: 280 characters total, including the "
        "link. Never break the URL."
    ),
    "LinkedIn": (
        "Tone: professional, ROI/benefit-first — write like a founder "
        "sharing an operational insight, not a consumer ad. Use short "
        "'broetry' style lines (one idea per line, a line break after each "
        "key sentence). Maximum 2 bullet points. No adverbs. No emoji."
    ),
    "Facebook": (
        "Tone: warm and conversational, like a friend sharing a genuine "
        "find. 1-2 emoji, no more. Must end with a short, open question "
        "that invites a reply (not a rhetorical one) — replies matter more "
        "than likes for reach here."
    ),
}


def _gemini_variety(base_text: str, platform: str, name: str) -> str:
    if not GEMINI_API_KEY:
        return base_text
    style_rule = _PLATFORM_STYLE_RULES.get(platform, "")
    prompt = (
        f'Rewrite this {platform} post about "{name}" so it reads like a real '
        f"person casually sharing a find, not a template. Keep the same link, "
        f"the same core facts (price/rating if mentioned), and the same hashtags "
        f"at the end, unchanged. Vary only the opening line and the wording in "
        f"between. Match the original language (Spanish or English).\n\n"
        f"Platform-specific style rules (2026): {style_rule}\n\n"
        f"Return ONLY the rewritten post text, nothing else.\n\n---\n{base_text}"
    )
    try:
        r = requests.post(
            GEMINI_ENDPOINT,
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.9, "maxOutputTokens": 400,
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            },
            timeout=20,
        )
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text or base_text
    except Exception as e:
        print(f"  [Social] Gemini variety falló ({e}), usando plantilla base")
        return base_text


# ── Kit de guerrilla: Reddit + Grupos de Facebook ─────────────────────────────
# Reestructuración a pedido de Sergio (2026-08-30): 100% manual, nada se
# publica solo. Cada producto (siempre de indexed_slugs() — nunca borradores)
# entrega 5 variaciones de comentario para Reddit + 5 posts de storytelling
# para Grupos de Facebook, listos para copiar/pegar por Telegram.

FB_LINK_REMINDER_ES = "(Recuerda dejar tu link en el primer comentario, no en este texto)"
FB_LINK_REMINDER_EN = "(Remember to drop your link in the first comment, not in this post)"

REDDIT_COMMENT_TEMPLATES_ES = [
    "Yo anduve dando vueltas con lo mismo hace poco. Terminé comparando un par "
    "de opciones y me quedé con {name} — {feature}. Dejo por acá lo que leí "
    "antes de decidirme, por si sirve: {url}",
    "No es la solución mágica, pero {name} me sacó de un apuro parecido. Lo "
    "encontré revisando reseñas cuando estaba en la misma duda que vos: {url}",
    "Pasé por lo mismo hace un tiempo. Lo que a mí me terminó convenciendo fue "
    "una comparativa de {name} — la dejo acá por si te ahorra la búsqueda: {url}",
    "No sé si ya lo mencionaron en el hilo, pero {name} me resolvió algo "
    "parecido sin gastar de más. Esto fue lo que me hizo decidir: {url}",
    "Esto no es publicidad, es literal lo que terminé usando yo: {name}. Lo "
    "leí acá antes de comprar y me sirvió para comparar: {url}",
]

REDDIT_COMMENT_TEMPLATES_EN = [
    "I was going back and forth on the same thing not long ago. Ended up "
    "comparing a few options and went with {name} — {feature}. Leaving what "
    "I read before deciding here in case it helps: {url}",
    "Not a magic fix, but {name} got me out of a pretty similar bind. Found "
    "it while reading reviews when I was stuck on the same decision: {url}",
    "Went through the exact same thing a while back. What actually convinced "
    "me was a write-up comparing {name} — leaving it here in case it saves "
    "you the search: {url}",
    "Not sure if it's been mentioned in the thread already, but {name} solved "
    "something similar for me without overspending. This is what made up my "
    "mind: {url}",
    "This isn't an ad, it's literally what I ended up using: {name}. Read "
    "this before buying and it helped me compare options: {url}",
]

FB_STORY_TEMPLATES_ES = [
    "Les cuento algo random: llevaba semanas posponiendo esto hasta que "
    "terminé probando {name}. No pensé que se iba a notar tanto la "
    "diferencia.\n\n" + FB_LINK_REMINDER_ES,
    "¿A alguien más le pasa que compra 2-3 veces antes de acertar? A mí me "
    "pasó justo con esto — recién con {name} sentí que valió la pena.\n\n"
    + FB_LINK_REMINDER_ES,
    "Historia corta: casi devuelvo mi primera compra en este rubro por "
    "decepción, hasta que alguien me recomendó {name}. Ahora entiendo por "
    "qué tanto hype.\n\n" + FB_LINK_REMINDER_ES,
    "No suelo postear estas cosas, pero necesitaba compartirlo — después de "
    "meses probando alternativas, {name} fue lo único que cumplió lo que "
    "prometía.\n\n" + FB_LINK_REMINDER_ES,
    "Verdad incómoda: gasté más de la cuenta probando otras opciones antes "
    "de dar con {name}. Si están en la misma duda, se las dejo para que "
    "miren con calma.\n\n" + FB_LINK_REMINDER_ES,
]

FB_STORY_TEMPLATES_EN = [
    "Random story: I'd been putting this off for weeks until I finally tried "
    "{name}. Didn't expect the difference to be this noticeable.\n\n"
    + FB_LINK_REMINDER_EN,
    "Anyone else buy the wrong thing 2-3 times before getting it right? "
    "That was me — only once I got {name} did it actually feel worth "
    "it.\n\n" + FB_LINK_REMINDER_EN,
    "Short story: I almost returned my first purchase in this category out "
    "of frustration, until someone recommended {name}. Now I get the "
    "hype.\n\n" + FB_LINK_REMINDER_EN,
    "Don't usually post stuff like this, but had to share — after months of "
    "trying alternatives, {name} was the only one that actually delivered.\n\n"
    + FB_LINK_REMINDER_EN,
    "Uncomfortable truth: I overspent trying other options before landing "
    "on {name}. If you're stuck on the same decision, leaving this here to "
    "look into.\n\n" + FB_LINK_REMINDER_EN,
]


def _template_guerrilla_kit(data: dict) -> dict:
    name = data["name"]
    url  = data["url"]
    features = data.get("features") or []
    lang = _detect_language(data)

    if lang == "es":
        feature = (features[0][0].lower() + features[0][1:]) if features else "cumplió mejor de lo que esperaba"
        reddit_templates, fb_templates = REDDIT_COMMENT_TEMPLATES_ES, FB_STORY_TEMPLATES_ES
    else:
        feature = (features[0][0].lower() + features[0][1:]) if features else "worked better than I expected"
        reddit_templates, fb_templates = REDDIT_COMMENT_TEMPLATES_EN, FB_STORY_TEMPLATES_EN

    return {
        "reddit_search_terms": build_reddit_search_terms(name, lang),
        "reddit_comments": [t.format(name=name, url=url, feature=feature) for t in reddit_templates],
        "fb_group_keywords": build_fb_group_keywords(name, lang),
        "fb_posts": [t.format(name=name) for t in fb_templates],
    }


def _prompt_facts(data: dict) -> str:
    """Metadata en formato neutro (siempre en inglés) para el contexto del
    prompt — evita que frases fijas en un idioma se cuelen en la salida
    cuando el idioma objetivo es el otro."""
    bits = []
    if data.get("price"):
        bits.append(f"Price: ${data['price']}")
    if data.get("rating"):
        reviews = f" ({data['reviews']} reviews)" if data.get("reviews") else ""
        bits.append(f"Rating: {data['rating']}/5{reviews}")
    return " | ".join(bits) or "No price/rating data available"


def _llm_guerrilla_kit(data: dict) -> dict | None:
    """Pide a Gemini el kit completo en JSON. Devuelve None ante cualquier
    falla (key ausente, HTTP, JSON inválido o incompleto) para caer al
    fallback local sin romper el envío diario."""
    if not GEMINI_API_KEY:
        return None

    name     = data["name"]
    url      = data["url"]
    facts    = _prompt_facts(data)
    features = ", ".join(data.get("features") or []) or "not specified"
    lang     = _detect_language(data)
    lang_name = "Spanish" if lang == "es" else "English"
    reminder  = FB_LINK_REMINDER_ES if lang == "es" else FB_LINK_REMINDER_EN

    prompt = f"""Product: {name}
Facts: {facts}
Key features: {features}
Article link (reference, not a direct sale): {url}

Detected content language of this product's page: {lang_name}.

Generate a "guerrilla marketing" distribution kit for this product. Respond
with ONLY this exact JSON, no extra text:

{{
  "reddit_search_terms": ["...", "...", "..."],
  "reddit_comments": ["...", "...", "...", "...", "..."],
  "fb_group_keywords": ["...", "...", "..."],
  "fb_posts": ["...", "...", "...", "...", "..."]
}}

STRICT LANGUAGE RULE: write every single field 100% in {lang_name}, the way
a native {lang_name} speaker would. Never mix languages within the same
string — zero Spanglish, zero code-switching — regardless of what language
this instruction itself is written in.

Rules:
- reddit_search_terms: 3 short phrases to find relevant Reddit threads,
  written in {lang_name} (e.g. "what baby monitor to buy reddit" in
  English, or "qué monitor de bebé comprar reddit" in Spanish).
- reddit_comments: 5 first-person variations, empathetic tone, like someone
  adding value to a real discussion — sharing a "discovery" or solving a
  specific pain point, NEVER a salesy tone. Each one must end with this
  link as a useful reference, not spam: {url}
- fb_group_keywords: 3 types/names of Facebook groups to search for based
  on this product's niche, written in {lang_name}.
- fb_posts: 5 short storytelling posts — a small relatable anecdote or
  problem that creates curiosity. Do NOT include the link. Each one must
  end EXACTLY with this line, unchanged: "{reminder}"
- No excessive emojis, no ad-speak ("don't miss out", "amazing deal").
  Sound like a real person, not a copywriter."""

    try:
        r = requests.post(
            GEMINI_ENDPOINT,
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.9, "maxOutputTokens": 1400,
                    "thinkingConfig": {"thinkingBudget": 0},
                    "responseMimeType": "application/json",
                },
            },
            timeout=25,
        )
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        kit = json.loads(text)
        required = ["reddit_search_terms", "reddit_comments", "fb_group_keywords", "fb_posts"]
        if not all(isinstance(kit.get(k), list) and kit.get(k) for k in required):
            raise ValueError("JSON incompleto")
        return kit
    except Exception as e:
        print(f"  [Social] LLM guerrilla kit falló ({e}), usando plantillas locales")
        return None


def generate_guerrilla_kit(data: dict, use_llm: bool = True) -> dict:
    if use_llm:
        kit = _llm_guerrilla_kit(data)
        if kit:
            return kit
    return _template_guerrilla_kit(data)


def format_guerrilla_messages(data: dict, kit: dict) -> tuple[str, str]:
    """Devuelve (mensaje_reddit, mensaje_facebook) — separados para que cada
    uno entre cómodo en un mensaje de Telegram y quede clarísimo cuál es cuál."""
    name = html.escape(data["name"])
    url  = data["url"]

    reddit_lines = [f"📌 <b>REDDIT — {name}</b>", f"<i>{url}</i>", ""]
    reddit_lines.append("<b>Términos de búsqueda</b> (para encontrar hilos donde comentar):")
    for t in kit["reddit_search_terms"]:
        reddit_lines.append(f"• {html.escape(t)}")
    reddit_lines.append("")
    reddit_lines.append("<b>Respuestas empáticas</b> — elegí 1 y adaptala al hilo que encuentres:")
    for i, c in enumerate(kit["reddit_comments"], 1):
        reddit_lines.append(f"\n<b>Variación {i}</b>\n<code>{html.escape(c)}</code>")

    fb_lines = [f"📘 <b>FACEBOOK GROUPS — {name}</b>", f"<i>{url}</i>", ""]
    fb_lines.append("<b>Grupos a buscar</b> según el nicho:")
    for g in kit["fb_group_keywords"]:
        fb_lines.append(f"• {html.escape(g)}")
    fb_lines.append("")
    fb_lines.append("<b>Publicaciones de storytelling</b> — elegí 1:")
    for i, p in enumerate(kit["fb_posts"], 1):
        fb_lines.append(f"\n<b>Variación {i}</b>\n<code>{html.escape(p)}</code>")

    return "\n".join(reddit_lines), "\n".join(fb_lines)


def _rating_line(data: dict) -> str:
    if data.get("rating") and data.get("reviews"):
        return f"⭐ {data['rating']} ({data['reviews']} reseñas en Amazon)"
    if data.get("rating"):
        return f"⭐ {data['rating']}/5"
    return ""


def _price_line(data: dict) -> str:
    if data.get("price"):
        try:
            return f"💵 ${float(data['price']):.0f}"
        except (TypeError, ValueError):
            return f"💵 {data['price']}"
    return ""


def _short_name(name: str, limit: int = 60) -> str:
    """Los títulos de Amazon suelen superar los 100 caracteres — usarlos
    completos en un hook social los hace ilegibles y, en X, puede consumir
    el límite de 280 caracteres por sí solo. Trunca en el último espacio
    antes del límite (mismo patrón que gen_hub_pages.py usa para tarjetas)."""
    if len(name) <= limit:
        return name
    cut = name[:limit].rsplit(" ", 1)[0]
    return (cut or name[:limit]).rstrip(",.|") + "…"


def build_copies(data: dict, use_gemini: bool = False) -> dict[str, str]:
    name  = _short_name(data["name"])
    url   = data["url"]
    year  = datetime.now().year
    hashtags = build_hashtags(name)
    rating_line = _rating_line(data)
    price_line  = _price_line(data)
    features = data.get("features") or []

    # ── Facebook: tono cálido, 1-2 emoji, cierra con pregunta abierta para
    # invitar respuestas (el algoritmo de afinidad de Meta pondera comentarios
    # más que likes) ──
    fb_lines = [random.choice(FB_HOOKS).format(name=name, year=year), ""]
    facts = " · ".join(x for x in (rating_line, price_line) if x)
    if facts:
        fb_lines.append(facts)
        fb_lines.append("")
    if features:
        fb_lines += [f"✅ {f}" for f in features]
        fb_lines.append("")
    fb_lines.append(random.choice(FB_CTA))
    fb_lines.append(url)
    fb_lines.append("")
    fb_lines.append(random.choice(FB_CLOSERS))
    fb_lines.append("")
    fb_lines.append(" ".join(hashtags[:3]))
    facebook = "\n".join(fb_lines)

    # ── X / Twitter: tono analista, máximo 1 hashtag (la saturación de tags
    # se penaliza), gancho con dato/número primero, <=280 caracteres ──
    facts = " · ".join(x for x in (rating_line, price_line) if x)
    hook = random.choice(X_HOOKS).format(emoji=random.choice(EMOJIS), name=name)
    x_lines = [hook, ""]
    if facts:
        x_lines.append(facts)
        x_lines.append("")
    x_lines.append(random.choice(X_CTA))
    x_lines.append(url)
    if hashtags:
        x_lines.append("")
        x_lines.append(hashtags[0])
    twitter = "\n".join(x_lines)
    if len(twitter) > X_MAX_CHARS:
        # Recorta primero lo prescindible (hashtag, luego facts) antes de
        # tocar el hook o el link — nunca cortar la URL a la mitad.
        twitter = "\n".join([hook, "", random.choice(X_CTA), url])
        if len(twitter) > X_MAX_CHARS:
            twitter = f"{hook}\n{url}"[:X_MAX_CHARS]

    # ── Pinterest (título + descripción + link + imagen) ──
    pin_title = f"{name} — Reseña Completa {year}"[:100]
    desc_base = data.get("description") or f"Todo lo que necesitas saber sobre {name} antes de comprar."
    pin_desc_parts = [desc_base]
    if features:
        pin_desc_parts.append(" ".join(f"✅ {f}." for f in features[:2]))
    pin_desc_parts.append(f"{random.choice(PIN_CTA)} {url}")
    pin_desc_parts.append(" ".join(hashtags[:5]))
    pin_description = " ".join(pin_desc_parts)[:500]

    pinterest = (
        f"Título del Pin: {pin_title}\n"
        f"Descripción: {pin_description}\n"
        f"Link de destino: {url}\n"
        f"Imagen: {data.get('image') or '(sin imagen detectada — subir manualmente)'}"
    )

    # ── LinkedIn: formato "broetry" (una idea por línea, saltos tras cada
    # oración clave), foco en ROI/beneficio operativo, máximo 2 viñetas ──
    li_lines = [random.choice(LI_HOOKS).format(name=name), ""]
    facts = " · ".join(x for x in (rating_line, price_line) if x)
    if facts:
        li_lines.append(facts)
        li_lines.append("")
    if features:
        li_lines += [f"• {f}" for f in features[:2]]
        li_lines.append("")
    li_lines.append(f"Análisis completo con pros, contras y precio actual: {url}")
    li_lines.append("")
    li_lines.append(" ".join(hashtags[:3]))
    linkedin = "\n".join(li_lines)

    # Pinterest queda con formato fijo (título/descripción/link/imagen) — no se
    # manda a reescribir con Gemini para no romper esa estructura.
    if use_gemini and GEMINI_API_KEY:
        facebook = _gemini_variety(facebook, "Facebook", name)
        twitter  = _gemini_variety(twitter, "X (Twitter)", name)
        linkedin = _gemini_variety(linkedin, "LinkedIn", name)

    return {"facebook": facebook, "twitter": twitter, "pinterest": pinterest, "linkedin": linkedin}


# ── Runner (export masivo a Markdown) ─────────────────────────────────────────

def run(limit: int = 0, platform: str = "all", only_slug: str | None = None,
        out_path: Path | None = None, use_gemini: bool = False) -> Path:
    slugs = [only_slug] if only_slug else indexed_slugs()
    if limit:
        slugs = slugs[:limit]

    if not slugs:
        print("  [Social] No hay páginas indexadas registradas en indexing_status.json todavía.")
        raise SystemExit(1)

    out_path = out_path or (OUT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md")
    out_path.parent.mkdir(exist_ok=True)

    blocks: list[str] = [
        f"# Copys de distribución social — TrendVortex ({datetime.now().strftime('%Y-%m-%d')})",
        f"\n{len(slugs)} página(s) indexada(s) incluida(s). Copiar y pegar manualmente, "
        f"no publicar la misma página en todas las redes el mismo día — elegí 1-2 por día "
        f"para que se vea como tráfico humano, no como bot.\n",
    ]

    ok = 0
    for slug in slugs:
        data = extract_page_data(slug)
        if data is None:
            print(f"  [Social] Saltada (sin HTML local): {slug}")
            continue
        copies = build_copies(data, use_gemini=use_gemini)
        ok += 1

        blocks.append(f"\n## {data['name']}\n`{data['url']}`\n")
        if platform in ("all", "facebook"):
            blocks.append(f"### Facebook\n```\n{copies['facebook']}\n```")
        if platform in ("all", "twitter", "x"):
            blocks.append(f"### X (Twitter)\n```\n{copies['twitter']}\n```")
        if platform in ("all", "linkedin"):
            blocks.append(f"### LinkedIn\n```\n{copies['linkedin']}\n```")
        if platform in ("all", "pinterest"):
            blocks.append(f"### Pinterest\n```\n{copies['pinterest']}\n```")

    out_path.write_text("\n".join(blocks), encoding="utf-8")
    print(f"  [Social] {ok}/{len(slugs)} copys generados -> {out_path}")
    return out_path


# ── Rotación diaria — 1 página/día por prioridad, 90 días de tracción ─────────

def _load_rotation() -> dict:
    if ROTATION_FILE.exists():
        try:
            return json.loads(ROTATION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"order": [], "pos": 0, "last_sent_date": None}


def _save_rotation(state: dict):
    ROTATION_FILE.write_text(json.dumps(state), encoding="utf-8")


def next_rotation_slug() -> str | None:
    """Siguiente slug a promover hoy. Recorre las indexadas de mayor a menor
    prioridad; al agotar la lista, la vuelve a armar (re-rankeando por si hay
    páginas nuevas indexadas) y empieza de nuevo — en 90 días esto da ~2
    vueltas completas a las 41 páginas actuales."""
    state = _load_rotation()
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_sent_date") == today:
        return None  # ya se mandó hoy, no duplicar

    if not state.get("order") or state["pos"] >= len(state["order"]):
        state["order"] = [slug for slug, _, _ in ranked_indexed_pages()]
        state["pos"] = 0

    if not state["order"]:
        return None

    slug = state["order"][state["pos"]]
    state["pos"] += 1
    state["last_sent_date"] = today
    _save_rotation(state)
    return slug


def _telegram_send(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [Social] Telegram no configurado — nada enviado")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=15,
        )
    except Exception as e:
        print(f"  [Social] Error Telegram: {e}")


def send_daily_batch(telegram_fn=None, use_llm: bool = True) -> str | None:
    """Manda a Telegram el kit guerrilla (Reddit + Facebook Groups) de la
    siguiente página en la rotación — SOLO indexadas (indexed_slugs()), nunca
    borradores. Se llama una vez al día desde main.py. Envía dos mensajes
    separados (Reddit / Facebook) para que quede clarísimo cuál es cuál."""
    slug = next_rotation_slug()
    if not slug:
        print("  [Social] Nada que enviar hoy")
        return None

    data = extract_page_data(slug)
    if data is None:
        print(f"  [Social] {slug} sin HTML local, saltada")
        return None

    kit = generate_guerrilla_kit(data, use_llm=use_llm)
    reddit_msg, facebook_msg = format_guerrilla_messages(data, kit)

    sender = telegram_fn or _telegram_send
    sender(reddit_msg)
    sender(facebook_msg)
    print(f"  [Social] Kit guerrilla enviado a Telegram: {slug}")
    return slug


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera copys sociales para páginas ya indexadas")
    parser.add_argument("--limit", type=int, default=0, help="Máximo de páginas a incluir")
    parser.add_argument("--platform",
                         choices=["all", "facebook", "twitter", "x", "linkedin", "pinterest"],
                         default="all")
    parser.add_argument("--slug", type=str, default=None, help="Generar solo para un slug puntual")
    parser.add_argument("--out", type=str, default=None, help="Ruta del archivo .md de salida")
    parser.add_argument("--gemini", action="store_true",
                         help="Usa GEMINI_API_KEY para variar la redacción (si está configurada)")
    parser.add_argument("--rank", action="store_true",
                         help="Solo imprime el ranking de prioridad de las páginas indexadas")
    parser.add_argument("--daily", action="store_true",
                         help="Dispara manualmente el envío diario a Telegram (kit guerrilla, rotación)")
    parser.add_argument("--preview", type=str, default=None, metavar="SLUG",
                         help="Imprime el kit guerrilla (Reddit + FB Groups) de un slug puntual, sin tocar la rotación ni enviar Telegram")
    parser.add_argument("--no-llm", action="store_true",
                         help="Con --preview/--daily, fuerza plantillas locales aunque haya GEMINI_API_KEY")
    args = parser.parse_args()

    if args.rank:
        for i, (slug, score, data) in enumerate(ranked_indexed_pages(), 1):
            price = f"${data['price']}" if data.get("price") else "s/precio"
            rating = f"{data['rating']}★({data['reviews']})" if data.get("rating") else "s/rating"
            print(f"{i:2d}. [{score:5.2f}] {data['name'][:45]:45s} {rating:14s} {price:8s} {data['url']}")
        raise SystemExit(0)

    if args.preview:
        data = extract_page_data(args.preview)
        if data is None:
            print(f"  [Social] {args.preview} no tiene HTML local")
            raise SystemExit(1)
        kit = generate_guerrilla_kit(data, use_llm=not args.no_llm)
        reddit_msg, facebook_msg = format_guerrilla_messages(data, kit)
        strip = lambda s: html.unescape(re.sub(r"</?[a-z]+>", "", s))
        print(strip(reddit_msg))
        print("\n" + "=" * 60 + "\n")
        print(strip(facebook_msg))
        raise SystemExit(0)

    if args.daily:
        send_daily_batch(use_llm=not args.no_llm)
        raise SystemExit(0)

    run(
        limit=args.limit,
        platform=args.platform,
        only_slug=args.slug,
        out_path=Path(args.out) if args.out else None,
        use_gemini=args.gemini,
    )
