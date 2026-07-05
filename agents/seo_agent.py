# -*- coding: utf-8 -*-
"""
agents/seo_agent.py — SEO Optimizer Agent
Usa Gemini Flash (gratuito, alta cuota) para generar:
  - Title tag optimizado (60 chars max)
  - Meta description (155 chars max)
  - Intro paragraph con keyword density natural
  - 3 bullets "why buy"
  - 5 FAQs estructuradas (schema FAQPage)
  - 5 long-tail keyword suggestions
"""
from __future__ import annotations
import os, json, re, time
from typing import Any

import requests

from agents.base import BaseAgent, AgentResult, AgentType

GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL   = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


class SEOAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            agent_type=AgentType.SEO_OPTIMIZER,
            name="SEOOptimizer",
            persona=(
                "Especialista en SEO para páginas de afiliados. Generas contenido "
                "que rankea en Google: títulos con keyword principal, metas que maximizan "
                "CTR, intros que retienen al usuario, FAQs que capturan featured snippets, "
                "y long-tail keywords con intención de compra. Nunca rellenas — cada "
                "palabra sirve para rankear o convertir."
            ),
        )

    def act(self, context: dict[str, Any]) -> AgentResult:
        """
        context requiere:
          - keyword: str
          - amazon: dict (titulo, precio, rating, reviews)
          - amazon_cat: str
          - trend_payload: dict (composite_score, hits_reciente)
          - subreddit: str
        """
        keyword   = context["keyword"]
        amazon    = context["amazon"]
        cat       = context.get("amazon_cat", "")
        trend     = context.get("trend_payload", {})
        subreddit = context.get("subreddit", "")

        if not GEMINI_KEY:
            # Sin key → fallback básico
            return AgentResult(
                agent_type=self.agent_type,
                success=True,
                reasoning="Sin GEMINI_API_KEY — usando SEO básico",
                payload=self._basic_seo(keyword, amazon, cat)
            )

        payload = self._call_gemini(keyword, amazon, cat, trend, subreddit)

        if payload:
            return AgentResult(
                agent_type=self.agent_type,
                success=True,
                reasoning=f"SEO generado con Gemini Flash | title='{payload.get('title','')[:40]}...'",
                payload=payload
            )
        else:
            return AgentResult(
                agent_type=self.agent_type,
                success=True,
                reasoning="Gemini falló — usando SEO básico",
                payload=self._basic_seo(keyword, amazon, cat)
            )

    # ── Gemini Flash call ─────────────────────────────────────────────────────

    def _call_gemini(self, keyword, amazon, cat, trend, subreddit) -> dict | None:
        anio = 2026

        prompt = f"""You are an expert SEO copywriter for affiliate review sites.

PRODUCT:
- Keyword: {keyword}
- Product name: {amazon['titulo']}
- Price: ${amazon['precio']:.2f}
- Rating: {amazon['rating']}★ out of 5 ({amazon['reviews']:,} reviews)
- Amazon category: {cat}
- Reddit community: r/{subreddit}
- Google Trends score: {trend.get('hits_reciente', 0):.0f}/100

Return a JSON object with EXACTLY these keys:
{{
  "title": "Best {keyword} in {anio} — [short compelling phrase] | TrendVortex",
  "meta_description": "155-char max meta. Include keyword, price hint, social proof.",
  "intro": "2-3 sentence engaging intro paragraph. Include keyword naturally, mention Reddit validation and review count.",
  "bullets": ["benefit 1", "benefit 2", "benefit 3"],
  "why_buy": "1-2 sentence why this product wins in this niche.",
  "faqs": [
    {{"q": "question 1 with keyword", "a": "answer 1"}},
    {{"q": "question 2", "a": "answer 2"}},
    {{"q": "question 3", "a": "answer 3"}},
    {{"q": "question 4", "a": "answer 4"}},
    {{"q": "question 5", "a": "answer 5"}}
  ],
  "long_tail_keywords": ["5 long-tail buying-intent keyword variations"]
}}

Rules:
- Title max 60 characters (before "| TrendVortex")
- Meta max 155 characters
- FAQs should target featured snippets (direct, factual answers)
- All content in English
- Focus on buying intent, not just information"""

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
        }

        for attempt in range(3):
            try:
                r = requests.post(
                    GEMINI_URL, params={"key": GEMINI_KEY},
                    json=body, timeout=30
                )
                if r.status_code == 429:
                    time.sleep(15 * (attempt + 1))
                    continue
                if r.status_code != 200:
                    break
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                # Extraer JSON del texto
                m = re.search(r"\{[\s\S]+\}", text)
                if m:
                    return json.loads(m.group())
            except Exception as e:
                print(f"  [SEO] Gemini error: {e}")
                time.sleep(5)
        return None

    # ── Fallback sin API ──────────────────────────────────────────────────────

    @staticmethod
    def _basic_seo(keyword: str, amazon: dict, cat: str) -> dict:
        anio = 2026
        k = keyword.title()
        return {
            "title": f"Best {k} {anio} — Reddit Picks | TrendVortex",
            "meta_description": (
                f"Best {keyword} under $150. {amazon['reviews']:,} Amazon reviews, "
                f"{amazon['rating']}★ avg. Reddit-validated. Updated {anio}."
            )[:155],
            "intro": (
                f"Finding the best {keyword} shouldn't take hours of research. "
                f"We scanned Reddit buying discussions and cross-referenced Google Trends "
                f"to surface the top-rated option: {amazon['reviews']:,} reviews, "
                f"{amazon['rating']}★, at ${amazon['precio']:.2f}."
            ),
            "bullets": [
                f"Reddit community-validated pick for {keyword}",
                f"{amazon['reviews']:,} verified Amazon reviews averaging {amazon['rating']}★",
                f"Price sweet spot: ${amazon['precio']:.2f} — under $150, above 4 stars"
            ],
            "why_buy": (
                f"With {amazon['reviews']:,} verified reviews and a {amazon['rating']}★ "
                f"average, this {keyword} consistently outperforms alternatives in its price range."
            ),
            "faqs": [
                {"q": f"What is the best {keyword}?",
                 "a": f"Based on Reddit community signals and {amazon['reviews']:,} Amazon reviews, the {amazon['titulo']} ({amazon['rating']}★) leads at ${amazon['precio']:.2f}."},
                {"q": f"Is {keyword} worth buying?",
                 "a": f"Yes — with {amazon['reviews']:,} verified reviews averaging {amazon['rating']}★ at ${amazon['precio']:.2f}, it's strong value."},
                {"q": f"Where to buy {keyword}?",
                 "a": "Amazon offers the best combination of price, verified reviews, and easy returns."},
                {"q": f"How much does {keyword} cost?",
                 "a": f"Quality {keyword} ranges from $30 to $150. Our top pick is ${amazon['precio']:.2f}."},
                {"q": f"What {keyword} does Reddit recommend?",
                 "a": f"Reddit communities consistently mention the {amazon['titulo']} as a top pick for {keyword}."},
            ],
            "long_tail_keywords": [
                f"best {keyword} for beginners",
                f"best {keyword} under 100 dollars",
                f"top rated {keyword} amazon",
                f"{keyword} reddit recommendations",
                f"best budget {keyword} {anio}",
            ]
        }
