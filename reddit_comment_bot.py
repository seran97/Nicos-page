# -*- coding: utf-8 -*-
"""
reddit_comment_bot.py — Semi-automático: encuentra hilos de Reddit donde
alguien pide recomendación de producto en un nicho que YA tenemos publicado
en trendvortex.tech, redacta un comentario natural (no promocional/obvio)
con Gemini, y lo manda a Telegram listo para copiar y pegar.

No publica nada solo — Reddit banea cuentas que auto-postean enlaces
repetidos, así que la decisión de postear (y con qué cuenta) la toma Sergio.

Uso:
  python reddit_comment_bot.py          # un ciclo
"""
from __future__ import annotations
import os, re, json
import feedparser, requests
from pathlib import Path
from dotenv import load_dotenv

from radar_nichos import SUBREDDITS, tiene_intent
from keyword_filter import extraer_keyword, es_keyword_producto

load_dotenv()

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
SITE_URL         = os.getenv("SITE_URL", "https://trendvortex.tech").rstrip("/")

SEEN_FILE = Path("reddit_comment_seen.txt")
DOCS_DIR  = Path(__file__).resolve().parent / "docs"


# ── Páginas ya publicadas ──────────────────────────────────────────────────────

def _slugs_publicados() -> set[str]:
    if not DOCS_DIR.exists():
        return set()
    return {p.name for p in DOCS_DIR.iterdir() if p.is_dir()}


def _keyword_to_slug(keyword: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
    return f"best-{slug}"


def _match_slug(keyword: str, slugs: set[str]) -> str | None:
    """Match exacto o por tokens compartidos (>=1 palabra clave en común,
    ignorando 'best')."""
    exact = _keyword_to_slug(keyword)
    if exact in slugs:
        return exact
    kw_tokens = set(keyword.lower().split()) - {"best", "the", "a", "for"}
    if not kw_tokens:
        return None
    for slug in slugs:
        slug_tokens = set(slug.replace("best-", "").split("-"))
        if kw_tokens & slug_tokens:
            return slug
    return None


# ── Redacción del comentario (Gemini) ──────────────────────────────────────────

def _redactar_comentario(post_title: str, keyword: str, page_url: str) -> str:
    if not GEMINI_API_KEY:
        return (f"Anduve buscando algo parecido hace poco, este artículo "
                f"me ayudó a decidir: {page_url}")

    prompt = (
        f'Reddit thread title: "{post_title}"\n'
        f"Someone is asking for help related to: {keyword}.\n\n"
        f"Write a short Reddit comment (3-5 sentences) as a MINI STORY, not a "
        f"recommendation. Structure it like this:\n"
        f"1. Open with a relatable complication or mess-up — something that went "
        f"wrong or was harder than expected for you, specific and a little "
        f"self-deprecating (e.g. 'ugh doing X the normal way was a disaster for me').\n"
        f"2. Mention briefly that you tried comparing a couple of options / did some "
        f"digging.\n"
        f"3. Land naturally on how it turned out easier once you found what you "
        f"needed, casually crediting a review/article you read — mention this link "
        f"as that source, worked into the sentence, not tacked on: {page_url}\n\n"
        f"Rules: sound like a real, slightly rambly redditor typing fast, not a "
        f"copywriter. Contractions, imperfect flow, no marketing words ('game "
        f"changer', 'highly recommend', 'check out'). No emoji, no hashtags. "
        f"Match the language of the thread title (English or Spanish). "
        f"Return ONLY the comment text, nothing else."
    )
    try:
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-2.5-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.8, "maxOutputTokens": 300,
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            },
            timeout=20,
        )
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text
    except Exception as e:
        print(f"  [RedditBot] Gemini fallo ({e}), usando comentario genérico")
        return (f"Anduve buscando algo parecido hace poco, este artículo "
                f"me ayudó a decidir: {page_url}")


# ── Telegram ────────────────────────────────────────────────────────────────

def _telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [RedditBot] Telegram no configurado")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=15,
        )
    except Exception as e:
        print(f"  [RedditBot] Error Telegram: {e}")


def _cargar_seen() -> set[str]:
    if SEEN_FILE.exists():
        return set(SEEN_FILE.read_text(encoding="utf-8").splitlines())
    return set()


def _guardar_seen(post_id: str):
    with SEEN_FILE.open("a", encoding="utf-8") as f:
        f.write(post_id + "\n")


# ── Escaneo ─────────────────────────────────────────────────────────────────

def run_ciclo():
    slugs = _slugs_publicados()
    if not slugs:
        print("  [RedditBot] No hay páginas publicadas todavía, nada que promover")
        return 0

    seen = _cargar_seen()
    encontrados = 0

    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/new/.rss"
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"  [RedditBot] Error r/{sub}: {e}")
            continue

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
            if not es_keyword_producto(keyword):
                continue

            slug = _match_slug(keyword, slugs)
            if not slug:
                continue  # no tenemos página para este nicho, saltar

            seen.add(post_id)
            _guardar_seen(post_id)

            page_url = f"{SITE_URL}/{slug}"
            link     = entry.get("link", "")
            comentario = _redactar_comentario(titulo, keyword, page_url)

            msg = (
                f"💬 <b>Oportunidad de comentario — r/{sub}</b>\n\n"
                f"<b>Hilo:</b> {titulo[:180]}\n"
                f"<b>Link del hilo:</b> {link}\n\n"
                f"<b>Nuestra página:</b> {page_url}\n\n"
                f"<b>Comentario sugerido (copia y pega, edítalo si quieres):</b>\n"
                f"<code>{comentario}</code>"
            )
            _telegram(msg)
            print(f"  [RedditBot] Oportunidad encontrada: r/{sub} → {slug}")
            encontrados += 1
            break  # máximo 1 por subreddit por ciclo, evita saturar Telegram

    print(f"  [RedditBot] {encontrados} oportunidades enviadas a Telegram")
    return encontrados


if __name__ == "__main__":
    run_ciclo()
