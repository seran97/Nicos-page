# -*- coding: utf-8 -*-
"""
keyword_filter.py — Validador de keywords compartido por radar_nichos.py,
macro_radar.py y orchestrator.py.

Por qué existe: keywords como "internet not working", "why god why" o
"power was out" (fragmentos de posts de Reddit sin intención real de
compra) pasaban el filtro viejo y terminaban generando páginas para
las que el checker de Amazon/eBay/AliExpress trae un producto random
sin ninguna relación (ver sesión 2026-07-20). El filtro viejo solo
bloqueaba por lista de palabras puntuales — esto agrega las palabras
de enlace/negación/queja que delatan una queja o pregunta en vez de
un nombre de producto, para que se filtren solas sin tener que listar
cada caso a mano.
"""
from __future__ import annotations

import re

# Relleno gramatical puro — no aporta nada al nombre de un producto, pero
# tampoco es señal de que NO sea un producto (se usa solo para limpiar
# tokens al extraer la keyword de un título).
FILLER = {
    "a", "an", "the", "for", "to", "in", "of", "on", "at", "is", "it", "my", "me", "i",
    "do", "be", "can", "any", "good", "best", "something", "there", "this", "that",
    "have", "want", "need", "get", "use", "just", "help", "with", "from", "what",
    "where", "how", "very", "too", "about", "one", "some", "up", "or", "and", "but",
    "by", "as", "un", "una", "el", "la", "los", "las", "de", "del", "para", "por",
    "que", "con", "como", "se", "mi", "no", "si", "es", "en", "al",
}

# Señales de que el texto es una queja/pregunta/troubleshooting de Reddit,
# no un nombre de producto (ej. "internet not working", "why god why",
# "power was out"). A diferencia de FILLER, la presencia de UNA sola de
# estas palabras descarta la keyword — por eso también viven en
# NO_PRODUCTO, para que el rechazo funcione aunque la keyword venga ya
# armada (de Gemini, de un CSV a mano, etc.) y no haya pasado por
# extraer_keyword().
RED_FLAGS = {
    # Verbos de enlace / auxiliares — indican fragmento de oración, no producto
    "was", "were", "are", "does", "did", "has", "had", "will", "would",
    "should", "could", "might", "am",
    # Negación — señal de queja/problema, no de compra
    "not", "wont", "won't", "dont", "don't", "cant", "can't", "cannot",
    "isn't", "wasn't", "weren't", "doesn't", "didn't", "hasn't", "hadn't",
    "never", "aint", "ain't",
    # Interjección / retórica típica de un rant, no de un producto
    "why", "god", "omg", "wtf", "ugh", "please", "pls", "seriously",
    # Fragmentos temporales/direccionales de una queja ("power was out", "won't start after")
    "out", "after", "before", "again", "still", "back", "ago", "anymore",
    # Malfunción/troubleshooting — "X not working/broken/stuck", no un producto
    "working", "worked", "works", "broken", "break", "breaks", "fix", "fixed",
    "fixing", "stuck", "jammed", "jam", "crash", "crashed", "crashing",
    "freeze", "freezing", "frozen", "leak", "leaking", "leaked", "died",
    "die", "dies", "dying", "start", "started", "starting", "restart",
    "reboot", "stopped", "stop", "stops",
}

STOPWORDS = FILLER | RED_FLAGS

# Palabras cuya presencia descarta la keyword aunque tenga >=2 tokens
# (temas, no productos: quejas, troubleshooting, charla genérica).
NO_PRODUCTO = RED_FLAGS | {
    "advice", "help", "question", "problem", "issue", "anyone", "people", "person",
    "family", "friend", "should", "would", "could", "trying", "feeling", "looking",
    "going", "think", "know", "tell", "says", "said", "asked", "time", "year", "day",
    "month", "week", "hours", "years", "days", "months", "weeks", "consejo", "ayuda",
    "alguien", "familia", "gente", "persona", "pregunta", "problema", "ciudad",
    "germany", "france", "spain", "italy", "mexico", "colombia", "report", "trip",
    "megathread", "june", "july", "august", "september", "october", "november", "december",
    "january", "february", "march", "april", "may", "update", "story", "experience",
    "mod", "mods", "weekly", "daily", "thread", "discussion", "rant", "vent", "share",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "inside", "scoop", "piss", "gremlin", "impending", "nino", "niño", "cottage",
    "ahead", "mass", "fresh", "give", "your", "take", "been", "seem", "another",
    "price", "cost", "cheap", "expensive", "sale", "deal", "discount", "offer",
    "recipe", "cook", "bake", "make", "prepare", "ingredients", "dish", "meal",
}


def extraer_keyword(titulo: str, intent_match: str) -> str:
    """Extrae una keyword de <=3 palabras de un título de Reddit, dado el
    fragmento de texto que matcheó el patrón de intención de compra."""
    limpio = re.sub(re.escape(intent_match), " ", titulo, flags=re.IGNORECASE)
    limpio = re.sub(r"[^\w\s]", " ", limpio)
    tokens = [w for w in limpio.split()
              if w.lower() not in STOPWORDS and len(w) > 2 and not w.isdigit()]

    # Máx 3 palabras — keywords más largas no rankean en Trends
    kw = " ".join(tokens[:3]).strip()

    # Validar que parece un producto: ≥2 tokens, sin verbos comunes de pregunta
    verbos_pregunta = {"looking", "using", "trying", "getting", "buying", "found", "bought",
                        "busco", "necesito", "buscando", "quiero", "tengo", "venden"}
    clean_tokens = [t for t in kw.split() if t.lower() not in verbos_pregunta]

    if len(clean_tokens) >= 2:
        return " ".join(clean_tokens[:3])
    # Fallback: tomar las primeras 3 palabras sustantivas del título original
    all_tokens = [w for w in re.sub(r"[^\w\s]", " ", titulo).split()
                  if w.lower() not in STOPWORDS and len(w) > 3 and not w.isdigit()]
    return " ".join(all_tokens[:3]) if all_tokens else titulo[:30]


def es_keyword_producto(kw: str) -> bool:
    """Descarta keywords que claramente no son productos buscables/comprables
    (quejas, troubleshooting, charla de Reddit sin intención de compra)."""
    if not kw or len(kw) < 4 or len(kw) > 60:
        return False
    tokens = kw.split()
    if len(tokens) < 2:
        return False
    if any(t.lower() in NO_PRODUCTO for t in tokens):
        return False
    return True
