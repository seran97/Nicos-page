# -*- coding: utf-8 -*-
"""gen_gift_guides.py — Christmas gift guides that curate existing reviews.

Each guide links to review pages already on the site (product data from
regen_manifest.json) and reuses the hub page design from gen_hub_pages.py.
No API calls. Prices are NOT printed: the manifest prices are months old,
so the cards send readers to Amazon for the current price.

Usage:  python gen_gift_guides.py
Then:   python -c "from page_generator import actualizar_sitemap, actualizar_index_html; actualizar_sitemap(); actualizar_index_html()"
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
import gen_hub_pages as hub  # also chdirs to radar_nichos/

SITE_URL = hub.SITE_URL
DOCS_DIR = hub.DOCS_DIR

GUIDES = [
    {
        "slug": "christmas-gifts-for-pet-lovers",
        "emoji": "🐾",
        "title": "Christmas Gifts for Pet Lovers",
        "h1": "Christmas Gifts for Dog and Cat Lovers",
        "desc": "Christmas gift ideas for dog and cat owners: pet cameras, water fountains, grooming gloves and travel gear picked from thousands of buyer reviews.",
        "intro": "The best gifts for pet owners solve a daily annoyance: a cat that won't drink enough water, fur on every couch, or the worry of leaving a dog alone while you travel for the holidays. Every pick below links to our full review, where we go through what buyers praise and what they complain about.",
        "tips": [
            "If you don't know the pet's size, pick something size-independent (camera, fountain, grooming glove) over beds or harnesses.",
            "Cat fountains need filter changes every few weeks; a pack of spare filters makes the gift complete.",
            "Pet cameras need 2.4 GHz Wi-Fi in most cases; check the recipient's router before buying.",
        ],
        "items": [
            ("best-pet-camera", "Lets them check in on their pet and talk to it while they travel to see family."),
            ("best-cat-water-fountain-ceramic-quiet", "Moving water gets many cats to drink more, and ceramic is easier to keep clean than plastic."),
            ("best-cat-water-fountain-stainless-steel-quiet", "A quieter stainless-steel option for bedrooms and small apartments."),
            ("best-pet-grooming-gloves-for-shedding", "A low-cost stocking stuffer that pulls loose fur during petting instead of off the couch."),
            ("best-keep-cat-entertained", "An interactive toy for indoor cats that get bored during long winter days."),
            ("best-portable-dog-water-bottle-for-travel", "For dog owners who hike or road-trip; it keeps water cold and doubles as a bowl."),
            ("best-collapsible-dog-bowl-for-travel", "Folds flat into a bag or glovebox for holiday road trips."),
        ],
    },
    {
        "slug": "christmas-gifts-for-gamers",
        "emoji": "🎮",
        "title": "Christmas Gifts for Gamers",
        "h1": "Christmas Gifts for Gamers and PC Lovers",
        "desc": "Christmas gift ideas for gamers: mechanical keyboards, headsets and mice picked from buyer reviews, with honest notes on who each one suits.",
        "intro": "Gaming gear is a safe gift only if it fits how the person plays. A clicky keyboard can annoy a roommate, and a console headset may not work on a PC. Each pick below says who it suits, and the full review covers compatibility and the most common complaints.",
        "tips": [
            "Ask (or check) whether they play on PC, PlayStation or Xbox; headset and controller compatibility differ.",
            "Keyboards: linear switches are quieter; clicky ones are loud on voice chat and in shared rooms.",
            "If they already own a good keyboard, a headset or mouse is the safer upgrade.",
        ],
        "items": [
            ("best-mechanical-keyboard", "A full-size mechanical keyboard from a known brand; a safe first step into mechanical keys."),
            ("best-keychron", "For someone who games and types all day: wireless, compact, with hot-swappable switches.", "Keychron Wireless Mechanical Keyboard"),
            ("best-wireless-mechanical-keyboard", "Typewriter-style keys that look great on a desk, with no cable clutter."),
            ("best-logitech-pop-keys-wireless-mechanical-keyboard", "Colorful and compact with emoji keys, a better fit for students and casual players than hardcore gamers.", "Logitech POP Keys Wireless Mechanical Keyboard"),
            ("best-gaming-headset", "An affordable headset for console players who want to hear teammates clearly."),
            ("best-gaming-mouse", "A lightweight wireless mouse for players who want faster aim without a cable."),
        ],
    },
    {
        "slug": "christmas-gifts-for-family",
        "emoji": "🎁",
        "title": "Christmas Gifts for the Whole Family",
        "h1": "Christmas Gift Ideas for Him, Her and the Whole Family",
        "desc": "Practical Christmas gift ideas for him, for her and for the family: wallets, board games, car gadgets, skincare and more, picked from buyer reviews.",
        "intro": "Practical gifts get used long after the wrapping paper is gone. This list mixes everyday-carry items, car gadgets, a skincare set and a game for the holiday table, each with a full review that covers what buyers liked and the most common complaints.",
        "tips": [
            "For wallets and jewelry, check the return policy in case style or size isn't right.",
            "Car gadgets: confirm the phone model (MagSafe or not) and the car's vent or dash layout.",
            "Skincare sets are safer gifts when they are fragrance-light and suit most skin types.",
        ],
        "items": [
            ("best-family-board-games-for-vacation", "Four compact classics for the whole family on Christmas Eve or a road trip."),
            ("best-leather-wallet-men", "A slim leather wallet with RFID blocking, a classic gift for him."),
            ("best-minimalist-stud-earrings", "Dainty sterling-silver evil-eye studs, a small and safe gift for her."),
            ("best-skin-care-routine", "A complete vitamin C set, an easy way to start a skincare routine."),
            ("best-insulated-water-bottle-for-hiking", "Keeps drinks cold all day, useful for the gym, the office or hiking."),
            ("best-car-phone-mount-magsafe", "A magnetic mount that charges an iPhone while it navigates."),
            ("best-portable-car-jump-starter", "A super-capacitor starter that stays connected, so a cold morning never ends with a dead battery. Needs a one-time install."),
            ("best-outdoor-string-lights-edison-bulb", "Warm string lights for the patio or balcony, for the holidays and beyond."),
        ],
    },
]


def productos(items, manifest):
    """Merges each slug with its manifest data; skips missing or non-Amazon pages."""
    datos = {m["slug"]: m for m in manifest}
    out = []
    for slug, motivo, *nombre in items:
        m = datos.get(slug)
        if not m or m.get("source") != "amazon" or not (DOCS_DIR / slug / "index.html").exists():
            print(f"  SKIP {slug} — not in manifest, not Amazon, or page missing")
            continue
        out.append({**m, "motivo": motivo, **({"titulo": nombre[0]} if nombre else {})})
    return out


def estilos():
    """Takes the CSS block of a hub page so guides look like the rest of the site."""
    muestra = hub.gen_hub_html("Pet Supplies", hub.CATEGORY_META["Pet Supplies"],
                               [{"slug": "x", "titulo": "x", "precio": 1.0, "rating": 4.5, "reviews": 10,
                                 "affiliate_url": "", "imagen_url": "", "amazon_cat": ""}])
    css = re.search(r"<style>(.*?)</style>", muestra, re.S).group(1)
    return css + ".card-why{font-size:.84rem;color:var(--text2)}"


def gen_guide_html(g, products, css):
    anio = datetime.now().year
    mes = datetime.now().strftime("%B %Y")
    total_reviews = sum(p["reviews"] for p in products)
    cards = ""
    for p in products:
        titulo = p["titulo"][:70] + ("..." if len(p["titulo"]) > 70 else "")
        cards += f"""
    <div class="prod-card">
      <a href="{SITE_URL}/{p['slug']}/" class="card-img-link">
        <img src="{p['imagen_url']}" alt="{titulo}" loading="lazy">
      </a>
      <div class="card-body">
        <div class="card-cat">{p['amazon_cat']}</div>
        <a href="{SITE_URL}/{p['slug']}/" class="card-title">{titulo}</a>
        <div class="card-meta">
          <span class="card-stars">{hub.stars(p['rating'])}</span>
          <span class="card-rating">{p['rating']}★</span>
          <span class="card-reviews">({p['reviews']:,} ratings)</span>
        </div>
        <p class="card-why">{p['motivo']}</p>
        <div class="card-actions">
          <a href="{SITE_URL}/{p['slug']}/" class="btn-review">Read Review →</a>
          <a href="{p['affiliate_url']}" class="btn-buy" rel="nofollow sponsored" target="_blank">Check Price →</a>
        </div>
      </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>{g['title']} {anio} | TrendVortex</title>
<meta name="description" content="{g['desc']}">
<link rel="canonical" href="{SITE_URL}/{g['slug']}/">
<meta property="og:title" content="{g['title']} {anio} | TrendVortex">
<meta property="og:description" content="{g['desc']}">
<meta property="og:image" content="{products[0]['imagen_url']}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<header class="site-header">
  <a class="site-logo" href="{SITE_URL}">Trend<span>Vortex</span></a>
  <span style="font-size:.7rem;color:var(--text3)">⚠ Affiliate disclosure</span>
</header>
<div class="breadcrumb">
  <a href="{SITE_URL}">Home</a> › Gift Guides › {g['title']}
</div>
<div class="hero">
  <span class="hero-emoji">{g['emoji']}</span>
  <h1>{g['h1']} ({anio})</h1>
  <p class="hero-sub">{len(products)} gift ideas picked from {total_reviews:,} buyer ratings, each linked to our full review. Updated {mes}.</p>
  <div class="trust-row">
    <span class="trust-item">✓ {len(products)} gift ideas</span>
    <span class="trust-item">✓ Full review for each pick</span>
    <span class="trust-item">✓ No paid placements</span>
  </div>
</div>
<div class="wrap">
<section class="sec">
  <div class="cat-intro">
    <p>{g['intro']}</p>
    <ul class="cat-tips">
      {"".join(f"<li>{t}</li>" for t in g['tips'])}
    </ul>
  </div>
  <div class="sec-eyebrow">Gift Ideas</div>
  <h2>{g['title']}: Our Picks for {anio}</h2>
  <div class="prod-grid">
    {cards}
  </div>
  <p style="font-size:.78rem;color:var(--text3);margin-top:18px">Ratings were taken from Amazon when each review was written. Prices change often during the holiday season, so check the current price on Amazon before buying.</p>
</section>
</div>
<footer>
  <strong>Affiliate disclosure:</strong> TrendVortex.tech earns a commission from Amazon when you buy through our links, at no extra cost to you.<br>
  <span style="display:block;margin-top:.4rem">© {anio} TrendVortex.tech · <a href="{SITE_URL}">Home</a> · Updated {mes}</span>
</footer>
</body></html>"""


def main():
    manifest = json.loads(Path("regen_manifest.json").read_text(encoding="utf-8"))
    css = estilos()
    for g in GUIDES:
        products = productos(g["items"], manifest)
        if len(products) < 3:
            print(f"  SKIP {g['slug']} — only {len(products)} products")
            continue
        destino = DOCS_DIR / g["slug"]
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "index.html").write_text(gen_guide_html(g, products, css), encoding="utf-8")
        print(f"  OK  /{g['slug']}/ — {len(products)} products")


if __name__ == "__main__":
    main()
