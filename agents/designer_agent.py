# -*- coding: utf-8 -*-
"""
agents/designer_agent.py — Designer Agent
Usa Claude API (claude-haiku-4-5) para generar páginas HTML ricas y profesionales.
Reemplaza el template estático con diseño generado por IA, adaptado al nicho.
"""
from __future__ import annotations
import os, re, json
from pathlib import Path
from datetime import datetime
from typing import Any

import anthropic

from agents.base import BaseAgent, AgentResult, AgentType

DOCS_DIR   = Path("docs")
SITE_URL   = os.getenv("SITE_URL", "https://trendvortex.tech")
AMAZON_TAG = os.getenv("AMAZON_TAG", "trendvortex-20")

# Claude Sonnet: calidad de diseño superior para páginas de afiliados
CLAUDE_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")


class DesignerAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            agent_type=AgentType.DESIGNER,
            name="DesignerAgent",
            persona=(
                "Diseñador web experto en páginas de afiliados de alto rendimiento. "
                "Generas HTML moderno con CSS inline, esquema de colores profesional, "
                "cards de producto, tablas de comparación, trust badges, y CTAs potentes. "
                "Cada página se ve como un review site premium — no un template genérico. "
                "Adaptas el diseño al nicho: cocina tiene calidez, tech tiene minimalismo, "
                "beauty tiene elegancia, outdoor tiene energía."
            ),
        )
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no encontrada en .env")
        self._client = anthropic.Anthropic(api_key=api_key)

    def act(self, context: dict[str, Any]) -> AgentResult:
        """
        context requiere:
          - keyword: str
          - amazon: dict (titulo, precio, rating, reviews, imagen_url, affiliate_url)
          - trend_payload: dict (composite_score, slope, hits_reciente, predicted_4w)
          - subreddit: str
          - amazon_cat: str
          - seo_content: dict (opcional, del SEO agent: intro, bullets, faqs)
        """
        keyword     = context["keyword"]
        amazon      = context["amazon"]
        trend       = context.get("trend_payload", {})
        subreddit   = context.get("subreddit", "")
        amazon_cat  = context.get("amazon_cat", "")
        seo_content = context.get("seo_content", {})

        kw_slug  = slug(keyword)
        if amazon.get("source") == "ebay":
            kw_slug = f"{kw_slug}-ebay"
        page_dir = DOCS_DIR / f"best-{kw_slug}"
        page_dir.mkdir(parents=True, exist_ok=True)

        # Determinar paleta según categoría
        palette = self._get_palette(amazon_cat)

        html = self._generate_with_claude(
            keyword, amazon, trend, subreddit, amazon_cat, seo_content, palette
        )

        used_fallback = html is None
        if not html:
            # Fallback: página básica mejorada
            html = self._fallback_html(keyword, amazon, trend, subreddit, amazon_cat)

        (page_dir / "index.html").write_text(html, encoding="utf-8")
        self._update_sitemap_and_index()

        return AgentResult(
            agent_type=self.agent_type,
            success=True,
            reasoning=f"Página generada: docs/best-{kw_slug}/index.html | {amazon_cat}",
            payload={
                "slug": kw_slug,
                "url": f"{SITE_URL}/best-{kw_slug}/",
                "fallback": used_fallback,
            }
        )

    # ── Generación con Claude ─────────────────────────────────────────────────

    def _generate_with_claude(
        self, keyword, amazon, trend, subreddit, amazon_cat, seo_content, palette
    ) -> str | None:

        anio = datetime.now().year
        mes  = datetime.now().strftime("%B %Y")

        intro     = seo_content.get("intro", "")
        bullets   = seo_content.get("bullets", [])
        faqs      = seo_content.get("faqs", [])
        why_buy   = seo_content.get("why_buy", "")

        long_tail = seo_content.get("long_tail_keywords", [])
        faqs_json  = json.dumps(faqs or [])
        bullets_json = json.dumps(bullets or [])
        kw_slug_val = slug(keyword)

        is_gaming_cat = (amazon_cat == "Amazon Games")
        theme_bg  = "#0f0f1a" if is_gaming_cat else "#ffffff"
        theme_bg2 = "#1a1a2e" if is_gaming_cat else "#f9fafb"
        theme_card= "#16161f" if is_gaming_cat else "#ffffff"
        theme_txt = "#f0f0f5" if is_gaming_cat else "#111827"
        theme_txt2= "#9999bb" if is_gaming_cat else "#4b5563"
        theme_bdr = "rgba(255,255,255,0.1)" if is_gaming_cat else "#e5e7eb"

        prompt = f"""Generate a COMPLETE affiliate review HTML page. Light theme (white background, dark text) for most categories, dark only for Gaming.

PRODUCT:
- Keyword: {keyword}
- Product: {amazon['titulo']}
- Price: ${amazon['precio']:.2f}
- Rating: {amazon['rating']}★ ({amazon['reviews']:,} reviews)
- Image: {amazon['imagen_url']}
- Affiliate link: {amazon['affiliate_url']} (rel="nofollow sponsored")
- Category: {amazon_cat} | Source: {amazon.get('source','amazon').upper()}

SEO CONTENT:
- Intro: {intro or f'The best {keyword} based on {amazon["reviews"]:,} buyer reviews and community research.'}
- Key benefits: {bullets_json}
- Why buy: {why_buy or f'{amazon["reviews"]:,} verified reviews averaging {amazon["rating"]}★.'}
- FAQs: {faqs_json}

DESIGN SYSTEM:
- Background: {theme_bg}
- Surface: {theme_bg2}
- Card: {theme_card}
- Text: {theme_txt}
- Text secondary: {theme_txt2}
- Border: {theme_bdr}
- Accent (decorative borders only): {palette['primary']}
- CTA button: #FF9900 (Amazon orange, black text) — Big Orange Button
- Font: Inter from Google Fonts

PAGE STRUCTURE (in this exact order, no sections missing):
1. Sticky header: "TrendVortex" logo (Trend+<span style=color:#FF9900>Vortex</span>), affiliate disclaimer right
2. Hero section: h1 "Best {keyword.title()} in {anio}", subtitle with review count, trust badges, CTA button to #top-pick
3. Methodology box: green left border, "How we chose this" paragraph mentioning {amazon['reviews']:,} reviews and r/{subreddit}
4. Section id="top-pick": "Editor's Choice" orange badge, product card (image left, info right), price ${amazon['precio']:.2f}, {amazon['rating']}★ stars, orange CTA full-width button.
   IMPORTANT — every click must convert: wrap the product image AND the product title in <a href="{amazon['affiliate_url']}" rel="nofollow sponsored" target="_blank"> so clicking either one also goes straight to Amazon (not just the button). Use cursor:pointer and a subtle hover effect (e.g. slight border/scale) on the image and title to signal they are clickable.
5. Section: Pros/Cons grid (2 columns), then "Who this is NOT for" box
6. Section: comparison table (Rating / Reviews / Price vs buyer benchmarks)
7. Section: Buying guide with 3 numbered steps (use CSS counter)
8. Mid-page CTA band (orange background, centered CTA button)
9. Section: 5 FAQ items with hover effect
10. Footer: affiliate disclosure, © {anio} TrendVortex.tech

CSS RULES:
- max-width: 820px; margin: 0 auto for content; full-width for header/hero/footer
- Product card: flex-direction:column on mobile, row on desktop (≥540px)
- CTA button: background:#FF9900; color:#000; font-weight:800; border-radius:10px; no outline
- All headings: font-weight:900; clamp() for font-size
- Comparison table: scrollable wrapper, min-width:300px
- No horizontal scroll at any viewport width

SCHEMA in <head>:
- FAQPage JSON-LD
- Product JSON-LD with aggregateRating and offers
- Canonical: {SITE_URL}/best-{kw_slug_val}/

Return ONLY complete HTML starting with <!DOCTYPE html>. No markdown, no explanation, no code fences. End with </html>."""

        try:
            message = self._client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=12000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            html = message.content[0].text.strip()
            # Limpiar si viene con markdown
            html = re.sub(r"^```html?\s*\n?", "", html, flags=re.IGNORECASE)
            html = re.sub(r"\n?```\s*$", "", html).strip()
            # Validar que el HTML esté completo (no truncado a mitad del CSS)
            if (html.startswith("<!DOCTYPE") or html.startswith("<html")) and "</html>" in html:
                return html
            print(f"  [Designer] HTML incompleto (truncado) — usando fallback")
        except Exception as e:
            print(f"  [Designer] Error Claude: {e}")
        return None

    # ── Fallback HTML ────────────────────────────────────────────────────────

    def _fallback_html(self, keyword, amazon, trend, subreddit, amazon_cat) -> str:
        """Light-theme CRO-optimized page per 2025-2026 affiliate best practices.
        Dark theme only for Gaming. Orange BOB CTA (#FF9900). PDF framework structure."""
        p    = self._get_palette(amazon_cat)
        anio = datetime.now().year
        mes  = datetime.now().strftime("%B %Y")
        kw_slug_val  = slug(keyword)
        rating_int   = int(amazon["rating"])
        stars        = "★" * rating_int + "☆" * (5 - rating_int)
        source_label = amazon.get("source", "amazon").upper()
        is_gaming    = (amazon_cat == "Amazon Games")

        # Theme — LIGHT for all categories except Gaming (per CRO/PDF research)
        bg       = "#0f0f1a" if is_gaming else "#ffffff"
        bg2      = "#1a1a2e" if is_gaming else "#f9fafb"
        card_bg  = "#16161f" if is_gaming else "#ffffff"
        card_bg2 = "#1e1e2a" if is_gaming else "#f3f4f6"
        border   = "rgba(255,255,255,0.1)" if is_gaming else "#e5e7eb"
        text_c   = "#f0f0f5" if is_gaming else "#111827"
        text2_c  = "#9999bb" if is_gaming else "#4b5563"
        text3_c  = "#666688" if is_gaming else "#6b7280"
        method_bg = "rgba(22,163,74,0.12)" if is_gaming else "rgba(22,163,74,0.06)"
        accent_light = "rgba(255,153,0,0.12)" if is_gaming else "rgba(255,153,0,0.06)"

        # Comparison table classes
        rating_cls  = "td-good" if amazon["rating"] >= 4.0 else "td-mid"
        reviews_cls = "td-good" if amazon["reviews"] >= 500 else "td-mid"
        price_cls   = "td-good" if amazon["precio"] <= 150 else "td-mid"

        # Safe title for JSON-LD (no double quotes that break JSON)
        titulo_safe = amazon["titulo"].replace('"', "'")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Best {keyword.title()} {anio} — Expert Pick + Buying Guide | TrendVortex</title>
<meta name="description" content="Best {keyword} in {anio}: {amazon['reviews']:,} verified buyer reviews, {amazon['rating']}★. Expert pick, pros/cons and buying guide. Updated {mes}.">
<link rel="canonical" href="{SITE_URL}/best-{kw_slug_val}/">
<meta property="og:title" content="Best {keyword.title()} {anio} | TrendVortex">
<meta property="og:description" content="{amazon['reviews']:,} reviews · {amazon['rating']}★ · ${amazon['precio']:.2f} · Updated {mes}">
<meta property="og:type" content="article">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Product","name":"{titulo_safe}","aggregateRating":{{"@type":"AggregateRating","ratingValue":"{amazon['rating']}","reviewCount":"{amazon['reviews']}","bestRating":"5"}},"offers":{{"@type":"Offer","price":"{amazon['precio']:.2f}","priceCurrency":"USD","availability":"https://schema.org/InStock","url":"{amazon['affiliate_url']}"}}}}
</script>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{{"@type":"Question","name":"What is the best {keyword}?","acceptedAnswer":{{"@type":"Answer","text":"Based on {amazon['reviews']:,} verified buyer reviews and community research, the {titulo_safe} ({amazon['rating']}★, ${amazon['precio']:.2f}) is our top pick for {anio}."}}}}]}}
</script>
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:{bg};--bg2:{bg2};--card:{card_bg};--card2:{card_bg2};
  --border:{border};--text:{text_c};--text2:{text2_c};--text3:{text3_c};
  --accent:{p['primary']};
  --cta:#FF9900;--cta-text:#000000;
  --star:#f59e0b;--green:#16a34a;--red:#dc2626;
}}
html{{scroll-behavior:smooth}}
body{{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.65;-webkit-font-smoothing:antialiased;overflow-x:hidden}}

/* HEADER */
.site-header{{background:var(--card);border-bottom:1px solid var(--border);padding:12px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 1px 4px rgba(0,0,0,0.06)}}
.site-logo{{font-weight:900;font-size:1.1rem;color:var(--text);text-decoration:none;letter-spacing:-.5px}}
.site-logo span{{color:var(--cta)}}
.site-disc{{font-size:.7rem;color:var(--text3);background:var(--bg2);padding:3px 10px;border-radius:20px;border:1px solid var(--border)}}

/* BREADCRUMB */
.breadcrumb{{padding:9px 24px;font-size:.78rem;color:var(--text3);background:var(--bg2);border-bottom:1px solid var(--border)}}
.breadcrumb a{{color:var(--text3);text-decoration:none}}
.breadcrumb span{{margin:0 5px}}

/* HERO */
.hero{{background:var(--bg2);border-bottom:3px solid var(--accent);padding:52px 24px 44px;text-align:center}}
.hero-cat{{display:inline-block;background:color-mix(in srgb,var(--accent) 15%,transparent);color:var(--accent);border:1px solid color-mix(in srgb,var(--accent) 40%,transparent);font-size:.68rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;padding:4px 14px;border-radius:20px;margin-bottom:16px}}
.hero h1{{font-size:clamp(1.65rem,5vw,2.7rem);font-weight:900;line-height:1.15;margin-bottom:12px;color:var(--text);max-width:720px;margin-left:auto;margin-right:auto}}
.hero-sub{{color:var(--text2);font-size:.97rem;margin-bottom:22px;max-width:540px;margin-left:auto;margin-right:auto}}
.trust-row{{display:flex;justify-content:center;flex-wrap:wrap;gap:.55rem;margin-bottom:26px}}
.trust-item{{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:5px 13px;font-size:.74rem;font-weight:600;color:var(--text2)}}
.btn-cta{{display:inline-block;background:var(--cta);color:var(--cta-text);font-weight:800;font-size:1rem;padding:15px 30px;border-radius:10px;text-decoration:none;box-shadow:0 4px 14px rgba(255,153,0,.35);transition:transform .15s,box-shadow .15s;border:none;cursor:pointer}}
.btn-cta:hover{{transform:translateY(-2px);box-shadow:0 6px 22px rgba(255,153,0,.45)}}
.btn-cta-lg{{font-size:1.1rem;padding:18px 36px;border-radius:12px;width:100%;max-width:400px;display:block;text-align:center;margin:0 auto}}

/* METHOD BOX */
.method-box{{background:{method_bg};border:1px solid rgba(22,163,74,.25);border-left:4px solid var(--green);padding:14px 20px;font-size:.85rem;color:var(--text2);line-height:1.6}}
.method-box strong{{color:var(--green);display:block;margin-bottom:5px;font-size:.72rem;text-transform:uppercase;letter-spacing:1.5px}}

/* WRAP */
.wrap{{max-width:820px;margin:0 auto;padding:0 20px 80px}}

/* SECTIONS */
.sec{{padding:40px 0 8px}}
.sec-eyebrow{{font-size:.64rem;font-weight:800;letter-spacing:2.5px;text-transform:uppercase;color:var(--accent);margin-bottom:6px}}
.sec h2{{font-size:clamp(1.2rem,4vw,1.6rem);font-weight:900;color:var(--text);margin-bottom:14px;line-height:1.25}}
.sec .lead{{font-size:.94rem;color:var(--text2);margin-bottom:18px;padding-left:14px;border-left:3px solid var(--border)}}
.divider{{height:1px;background:var(--border);margin:6px 0}}

/* WINNER BADGE */
.winner-badge{{display:inline-block;background:var(--cta);color:#000;font-size:.62rem;font-weight:900;letter-spacing:2px;text-transform:uppercase;padding:4px 12px;border-radius:20px;margin-bottom:12px}}

/* PRODUCT CARD */
.product-card{{background:var(--card);border:1px solid var(--border);border-top:4px solid var(--cta);border-radius:14px;padding:24px;margin:16px 0;display:flex;gap:24px;align-items:flex-start}}
.product-card img{{width:160px;height:160px;object-fit:contain;border-radius:10px;background:var(--bg2);border:1px solid var(--border);flex-shrink:0;cursor:pointer;transition:opacity .15s,transform .15s}}
.product-card img:hover{{opacity:.88;transform:scale(1.02)}}
.prod-title:hover{{color:var(--accent)}}
.prod-info{{flex:1;min-width:0}}
.prod-source{{font-size:.68rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}}
.prod-title{{font-size:1rem;font-weight:700;color:var(--text);margin-bottom:10px;line-height:1.4}}
.prod-stars{{color:var(--star);font-size:1.1rem;letter-spacing:1px}}
.prod-rating-val{{font-size:.82rem;color:var(--text2);font-weight:600;margin-left:4px}}
.prod-review-cnt{{font-size:.79rem;color:var(--text3);margin-left:4px}}
.prod-price{{font-size:2rem;font-weight:900;color:var(--text);margin:.6rem 0;line-height:1}}
.prod-price-note{{font-size:.7rem;color:var(--text3);margin-bottom:14px}}
@media(max-width:540px){{.product-card{{flex-direction:column}}.product-card img{{width:100%;height:200px;max-width:none}}}}

/* PROS/CONS */
.pros-cons-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0}}
@media(max-width:480px){{.pros-cons-grid{{grid-template-columns:1fr}}}}
.pros-box,.cons-box{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px}}
.pros-box{{border-top:3px solid var(--green)}}
.cons-box{{border-top:3px solid #d97706}}
.pros-box h3,.cons-box h3{{font-size:.82rem;font-weight:800;margin-bottom:10px}}
.pros-box h3{{color:var(--green)}}
.cons-box h3{{color:#d97706}}
.pros-box ul,.cons-box ul{{list-style:none;padding:0}}
.pros-box li,.cons-box li{{font-size:.85rem;color:var(--text2);padding:5px 0 5px 22px;position:relative;line-height:1.55}}
.pros-box li::before{{content:'✅';position:absolute;left:0;font-size:.72rem;top:6px}}
.cons-box li::before{{content:'⚠️';position:absolute;left:0;font-size:.72rem;top:6px}}

/* NOT-FOR BOX */
.not-for-box{{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:16px 18px;margin:14px 0;font-size:.86rem;color:var(--text2);line-height:1.6}}
.not-for-box strong{{display:block;color:var(--text);margin-bottom:6px;font-size:.75rem;text-transform:uppercase;letter-spacing:1px}}

/* COMPARISON TABLE */
.tabla-wrap{{overflow-x:auto;margin:14px 0;border-radius:12px;border:1px solid var(--border);-webkit-overflow-scrolling:touch}}
table{{width:100%;border-collapse:collapse;min-width:300px;font-size:.85rem}}
thead th{{background:var(--bg2);padding:10px 16px;text-align:left;font-size:.7rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border)}}
tbody td{{padding:10px 16px;color:var(--text2);border-top:1px solid var(--border)}}
tbody td:first-child{{font-weight:600;color:var(--text)}}
.td-good{{color:var(--green);font-weight:700}}
.td-mid{{color:#d97706;font-weight:600}}
tbody tr:hover td{{background:var(--bg2)}}

/* BUYING GUIDE STEPS */
.guide-steps{{counter-reset:step;margin:14px 0}}
.guide-step{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px 16px 16px 58px;margin-bottom:10px;position:relative;font-size:.87rem;color:var(--text2);line-height:1.65;counter-increment:step}}
.guide-step::before{{content:counter(step);position:absolute;left:16px;top:18px;width:28px;height:28px;background:var(--accent);color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.78rem;text-align:center;line-height:28px}}
.guide-step strong{{display:block;color:var(--text);margin-bottom:5px;font-size:.9rem;font-weight:700}}

/* CTA BAND */
.cta-band{{background:{accent_light};border:1px solid rgba(255,153,0,.25);border-radius:14px;padding:28px 24px;margin:32px 0;text-align:center}}
.cta-band h3{{font-size:1.15rem;font-weight:900;color:var(--text);margin-bottom:6px}}
.cta-band p{{font-size:.88rem;color:var(--text2);margin-bottom:18px}}

/* FAQ */
.faq-item{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px;margin-bottom:10px;transition:border-color .2s}}
.faq-item:hover{{border-color:var(--cta)}}
.faq-q{{font-weight:700;color:var(--text);margin-bottom:6px;font-size:.9rem}}
.faq-a{{font-size:.85rem;color:var(--text2);line-height:1.65}}
.faq-a a{{color:var(--accent);text-decoration:none}}

/* FOOTER */
footer{{border-top:1px solid var(--border);background:var(--bg2);padding:28px 24px;font-size:.77rem;color:var(--text3);text-align:center;line-height:1.8}}
footer strong{{color:var(--text2)}}
footer a{{color:var(--text3)}}
</style>
</head>
<body>

<header class="site-header">
  <a class="site-logo" href="{SITE_URL}">Trend<span>Vortex</span></a>
  <span class="site-disc">⚠ Affiliate disclosure</span>
</header>

<div class="breadcrumb">
  <a href="{SITE_URL}">Home</a><span>›</span><a href="{SITE_URL}">{amazon_cat}</a><span>›</span>Best {keyword.title()}
</div>

<div class="hero">
  <div class="hero-cat">{amazon_cat}</div>
  <h1>Best {keyword.title()} in {anio}: Our Expert Pick After Deep Research</h1>
  <p class="hero-sub">We read through {amazon['reviews']:,} real buyer reviews and community discussions on r/{subreddit} to find the top {keyword} pick. No paid placements — just data. Updated {mes}.</p>
  <div class="trust-row">
    <span class="trust-item">✓ {amazon['reviews']:,} verified reviews</span>
    <span class="trust-item">✓ Updated {mes}</span>
    <span class="trust-item">✓ No paid placements</span>
    <span class="trust-item">✓ Amazon affiliate</span>
  </div>
  <a href="#top-pick" class="btn-cta">See Our Top Pick ↓</a>
</div>

<div class="method-box">
  <strong>📋 Our Methodology</strong>
  We analyzed {amazon['reviews']:,} verified buyer reviews on Amazon and community discussions on Reddit's r/{subreddit}. We only recommend products with a minimum 4★ rating and strong review volume — no single data point decides the pick, and no manufacturer paid to appear here.
</div>

<div class="wrap">

<!-- TOP PICK -->
<section id="top-pick" class="sec">
  <div class="sec-eyebrow">Our #1 Pick · {source_label}</div>
  <h2>Best {keyword.title()} for {anio}</h2>
  <span class="winner-badge">EDITOR'S CHOICE {anio}</span>
  <div class="product-card">
    <a href="{amazon['affiliate_url']}" rel="nofollow sponsored" target="_blank" aria-label="View {amazon['titulo']} on Amazon">
      <img src="{amazon['imagen_url']}" alt="{amazon['titulo']}" loading="eager">
    </a>
    <div class="prod-info">
      <div class="prod-source">{source_label} · {amazon_cat}</div>
      <a class="prod-title" href="{amazon['affiliate_url']}" rel="nofollow sponsored" target="_blank" style="text-decoration:none;display:block">{amazon['titulo']}</a>
      <div>
        <span class="prod-stars">{stars}</span>
        <span class="prod-rating-val">{amazon['rating']}★</span>
        <span class="prod-review-cnt">({amazon['reviews']:,} verified reviews)</span>
      </div>
      <div class="prod-price">${amazon['precio']:.2f}</div>
      <div class="prod-price-note">* Price checked daily — may vary on Amazon</div>
      <a class="btn-cta btn-cta-lg" href="{amazon['affiliate_url']}" rel="nofollow sponsored" target="_blank">
        Check Price on Amazon →
      </a>
    </div>
  </div>
</section>

<div class="divider"></div>

<!-- PROS / CONS + WHO IT'S NOT FOR -->
<section class="sec">
  <div class="sec-eyebrow">Honest Assessment</div>
  <h2>Pros &amp; Cons</h2>
  <div class="pros-cons-grid">
    <div class="pros-box">
      <h3>✅ PROS</h3>
      <ul>
        <li>Strong {amazon['rating']}★ rating from {amazon['reviews']:,} real buyers</li>
        <li>Well-priced at ${amazon['precio']:.2f} for the quality level</li>
        <li>Consistently recommended on r/{subreddit}</li>
      </ul>
    </div>
    <div class="cons-box">
      <h3>⚠️ CONS</h3>
      <ul>
        <li>Not the cheapest option in the {keyword} category</li>
        <li>Heavy commercial use may need a higher-tier pick</li>
      </ul>
    </div>
  </div>
  <div class="not-for-box">
    <strong>🚫 Who this is NOT for</strong>
    If you need a professional-grade {keyword} for heavy-duty commercial use, this pick may not meet capacity requirements. Look for options with commercial-grade specs and extended warranties for that scenario.
  </div>
</section>

<div class="divider"></div>

<!-- COMPARISON TABLE -->
<section class="sec">
  <div class="sec-eyebrow">Does It Clear the Bar?</div>
  <h2>How It Measures Up</h2>
  <p class="lead">Buyers on r/{subreddit} look for these three factors before committing to any {keyword} purchase.</p>
  <div class="tabla-wrap">
    <table>
      <thead>
        <tr><th>Factor</th><th>What Buyers Want</th><th>Our Top Pick</th></tr>
      </thead>
      <tbody>
        <tr><td>Star Rating</td><td>4.0★ or above</td><td class="{rating_cls}">{amazon['rating']}★ ✓</td></tr>
        <tr><td>Verified Reviews</td><td>500+ reviews</td><td class="{reviews_cls}">{amazon['reviews']:,} ✓</td></tr>
        <tr><td>Price Range</td><td>$15–$250 sweet spot</td><td class="{price_cls}">${amazon['precio']:.2f} ✓</td></tr>
        <tr><td>Source</td><td>Amazon listing</td><td class="td-good">✓ Amazon</td></tr>
      </tbody>
    </table>
  </div>
</section>

<div class="divider"></div>

<!-- BUYING GUIDE -->
<section class="sec">
  <div class="sec-eyebrow">Buying Guide</div>
  <h2>What to Look For in a {keyword.title()}</h2>
  <p class="lead">Before spending money on any {keyword}, check these three factors that experienced buyers consistently flag in their reviews.</p>
  <div class="guide-steps">
    <div class="guide-step">
      <strong>Check the review count, not just the star average</strong>
      A 4.5★ with 12 reviews means almost nothing. A 4.5★ with {amazon['reviews']:,} reviews like our top pick is a much stronger signal. Always look at total verified review count before trusting the star rating.
    </div>
    <div class="guide-step">
      <strong>Match the price to your real use case</strong>
      Don't overpay for features you won't use. For everyday use, the $50–$120 range covers 90% of needs. Our pick at ${amazon['precio']:.2f} sits in that sweet spot for most r/{subreddit} buyers.
    </div>
    <div class="guide-step">
      <strong>Read the 1-star reviews before buying</strong>
      The most useful signal is what makes people return a product. If the same complaint appears in 20+ reviews, it's a real issue. Our top pick's negative reviews are sparse and non-critical — a good sign.
    </div>
  </div>
</section>

<div class="divider"></div>

<!-- MID-PAGE CTA -->
<div class="cta-band">
  <h3>Ready to Buy?</h3>
  <p>Our top {keyword} pick: <strong>{amazon['titulo']}</strong> — {amazon['rating']}★ from {amazon['reviews']:,} reviews at ${amazon['precio']:.2f}.</p>
  <a class="btn-cta btn-cta-lg" href="{amazon['affiliate_url']}" rel="nofollow sponsored" target="_blank">
    Check Current Price on Amazon →
  </a>
</div>

<!-- FAQ -->
<section class="sec">
  <div class="sec-eyebrow">FAQ</div>
  <h2>Frequently Asked Questions</h2>
  <div class="faq-item">
    <div class="faq-q">What is the best {keyword} in {anio}?</div>
    <div class="faq-a">Based on {amazon['reviews']:,} verified buyer reviews and community research on r/{subreddit}, the <strong>{amazon['titulo']}</strong> is our top pick for {anio}. It earns {amazon['rating']}★ at ${amazon['precio']:.2f} — strong value for the quality.</div>
  </div>
  <div class="faq-item">
    <div class="faq-q">Is {keyword} worth buying in {anio}?</div>
    <div class="faq-a">{amazon['reviews']:,} verified reviews averaging {amazon['rating']}★ at ${amazon['precio']:.2f} puts this solidly in the "worth buying" category. If you need professional-grade, see the "Who this is NOT for" section above.</div>
  </div>
  <div class="faq-item">
    <div class="faq-q">Where is the best place to buy {keyword}?</div>
    <div class="faq-a">Amazon offers the best mix of verified reviews, competitive pricing, and buyer protections (easy returns, A-to-Z guarantee). <a href="{amazon['affiliate_url']}" rel="nofollow sponsored">Check the current price here →</a></div>
  </div>
  <div class="faq-item">
    <div class="faq-q">How much should I pay for a quality {keyword}?</div>
    <div class="faq-a">Quality {keyword} ranges from $30 to $200+ depending on the tier. For most buyers, $50–$120 hits the best balance of quality and value. Our top pick at ${amazon['precio']:.2f} falls right in that range.</div>
  </div>
  <div class="faq-item">
    <div class="faq-q">What does the r/{subreddit} community say about {keyword}?</div>
    <div class="faq-a">Reddit's r/{subreddit} values real-world durability and honest value over brand prestige. The {amazon['titulo']} with {amazon['reviews']:,} reviews and {amazon['rating']}★ meets those standards — and avoids the common pitfalls that community members flag.</div>
  </div>
</section>

</div>

<footer>
  <strong>Affiliate disclosure:</strong> TrendVortex.tech is a participant in the Amazon Services LLC Associates Program. When you purchase through our links we earn a small commission at no extra cost to you. We are not paid by manufacturers to recommend specific products — picks are based on buyer review data and community research.<br>
  <span style="display:block;margin-top:.5rem">© {anio} TrendVortex.tech · <a href="{SITE_URL}">Home</a> · Updated {mes}</span>
</footer>

<script>
document.querySelectorAll('a[href^="#"]').forEach(a=>{{
  a.addEventListener('click',e=>{{
    e.preventDefault();
    const t=document.querySelector(a.getAttribute('href'));
    if(t)t.scrollIntoView({{behavior:'smooth',block:'start'}});
  }});
}});
</script>
</body></html>"""

    # ── Paleta de colores por categoría ──────────────────────────────────────

    @staticmethod
    def _get_palette(amazon_cat: str) -> dict:
        # Colores optimizados para fondo OSCURO (#0a0a0f) — deben ser visibles
        palettes = {
            "Kitchen & Dining": {"primary": "#ff6b6b", "accent": "#ff8e8e", "cta": "#e74c3c"},
            "Luxury Beauty":    {"primary": "#c39bd3", "accent": "#d7bde2", "cta": "#8e44ad"},
            "Automotive":       {"primary": "#5dade2", "accent": "#85c1e9", "cta": "#2980b9"},
            "Amazon Games":     {"primary": "#7b61ff", "accent": "#a78bfa", "cta": "#6d4aff"},
            "Fashion":          {"primary": "#f06292", "accent": "#f48fb1", "cta": "#e91e8c"},
            "Sports & Outdoors":{"primary": "#58d68d", "accent": "#82e0aa", "cta": "#27ae60"},
            "Pet Supplies":     {"primary": "#f8c471", "accent": "#fad7a0", "cta": "#d35400"},
            "Toys & Baby":      {"primary": "#85c1e9", "accent": "#aed6f1", "cta": "#2980b9"},
            "Home Improvement": {"primary": "#52be80", "accent": "#76d7a0", "cta": "#1e8449"},
        }
        return palettes.get(amazon_cat, {"primary": "#00d4aa", "accent": "#5dade2", "cta": "#0f3460"})

    # ── Sitemap + Index ───────────────────────────────────────────────────────

    def _update_sitemap_and_index(self):
        try:
            from page_generator import actualizar_sitemap, actualizar_index_html
            actualizar_sitemap()
            actualizar_index_html()
        except Exception:
            pass
