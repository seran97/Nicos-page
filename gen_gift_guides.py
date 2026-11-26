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
            ("best-minimalist-stud-earrings", "Dainty sterling-silver studs with cubic zirconia, a small and safe gift for her."),
            ("best-skin-care-routine", "A complete vitamin C set, an easy way to start a skincare routine."),
            ("best-insulated-water-bottle-for-hiking", "Keeps drinks cold all day, useful for the gym, the office or hiking."),
            ("best-car-phone-mount-magsafe", "A magnetic mount that charges an iPhone while it navigates."),
            ("best-portable-car-jump-starter", "A super-capacitor starter that stays connected, so a cold morning never ends with a dead battery. Needs a one-time install."),
            ("best-outdoor-string-lights-edison-bulb", "Warm string lights for the patio or balcony, for the holidays and beyond."),
        ],
    },
    {
        "slug": "christmas-gifts-for-runners",
        "emoji": "👟",
        "title": "Christmas Gifts for Runners",
        "h1": "Christmas Gifts for Runners: Nike, Adidas, New Balance and More",
        "desc": "Christmas gift ideas for runners: Nike Pegasus, Vomero and Free Run, Adidas Hyperboost, New Balance FuelCell and Under Armour running shoes, with honest notes on who each one suits.",
        "intro": "Running shoes are the gift runners actually use every week, but only if the size and the type of running fit. A cushioned road shoe, a trail shoe and a lightweight trainer feel very different. Each pick below says who it suits and links to our full review; prices and sizes change fast in December, so check the store before buying.",
        "tips": [
            "Ask (or check their current pair) for the exact size and width; running shoe sizes vary between brands.",
            "Road shoes are for pavement and treadmills; trail shoes have more grip and protection for dirt and rocks.",
            "Buy from a store with free returns or keep the gift receipt, so they can swap the size after Christmas.",
        ],
        "items": [
            ("best-nike-pegasus-42", "Nike's best-known daily trainer: cushioned and durable for easy runs and long weekend miles.", "Nike Women's Pegasus 41 Running Shoes"),
            ("best-nike-vomero-plus", "Nike's softest road shoe, for runners who want maximum cushioning on long, easy runs.", "Nike Women's Vomero Plus Running Shoes"),
            ("best-nike-trail-running-shoes", "A waterproof trail shoe for winter runs on wet dirt and mud.", "Nike Men's Pegasus Trail 5 GORE-TEX"),
            ("best-nike-men-s-free-run-5-0-running-shoes", "Light and flexible, a good fit for short runs, the gym and everyday wear.", "Nike Men's Free Run 5.0"),
            ("best-hyperboost-edge-running-shoes-ebay", "Adidas' cushioned road shoe, bought on eBay, where sizes and colors that sold out elsewhere sometimes appear.", "Adidas Women's Hyperboost Edge Running Shoes"),
            ("best-new-balance-running-shoes", "A light, bouncy shoe for faster runs and tempo days.", "New Balance Men's FuelCell Rebel v5"),
            ("best-under-armour-running-shoes", "An affordable, cushioned shoe for new runners and gym sessions.", "Under Armour Men's Charged Assert 11"),
        ],
    },
    # 26-nov-2026: guías nuevas con productos de las páginas profundas (datos leídos en Amazon el 18-nov-2026)
    {
        "slug": "christmas-gifts-for-skincare-lovers",
        "emoji": "🧴",
        "title": "Christmas Gifts for Skincare Lovers",
        "h1": "Skincare Gifts They Will Actually Use: Drugstore Favorites",
        "desc": "Skincare Christmas gifts from CeraVe, Neutrogena, The Ordinary, Paula's Choice, TruSkin, EltaMD and Supergoop, each with tens of thousands of Amazon ratings and a note on which skin type it suits.",
        "intro": "Skincare is a great gift when it matches the person's skin, and a drawer-filler when it does not. That is why every pick below is a well-known product with tens of thousands of owner ratings, and why each card says which skin type it suits. When in doubt, gentle basics (a cleanser, a moisturizer, a daily sunscreen) are the safest choice.",
        "tips": [
            "Not sure of their skin type? Pick fragrance-free basics like a gentle cleanser or moisturizer.",
            "Actives like retinol, vitamin C and exfoliating acids are better for people who already use skincare regularly.",
            "A daily sunscreen they like the feel of is one of the most useful skincare gifts you can give.",
        ],
        "items": [
            {"slug": "best-skin-care-routine", "asin": "B07RL88DD2", "titulo": "CeraVe Hydrating Facial Cleanser", "rating": 4.7, "reviews": 133678, "cat": "Cleanser",
             "motivo": "A gentle, fragrance-free cleanser for normal to dry skin; a safe pick for almost anyone."},
            {"slug": "best-skin-care-routine", "asin": "B00NR1YQHM", "titulo": "Neutrogena Hydro Boost Water Gel", "rating": 4.6, "reviews": 88265, "cat": "Moisturizer",
             "motivo": "A light gel moisturizer that oily and combination skin can wear without feeling greasy."},
            {"slug": "best-skin-care-routine", "asin": "B00TTD9BRC", "titulo": "CeraVe Moisturizing Cream", "rating": 4.7, "reviews": 149766, "cat": "Moisturizer",
             "motivo": "A rich cream for dry skin on the face and body, very welcome in winter."},
            {"slug": "best-serum-face", "asin": "B0DDQ4MSXS", "titulo": "The Ordinary Niacinamide 10% + Zinc 1%", "rating": 4.7, "reviews": 71311, "cat": "Serum",
             "motivo": "A low-cost serum for oily, blemish-prone skin and visible pores; a good stocking stuffer."},
            {"slug": "best-serum-face", "asin": "B00949CTQQ", "titulo": "Paula's Choice 2% BHA Liquid Exfoliant", "rating": 4.5, "reviews": 117275, "cat": "Exfoliant",
             "motivo": "A cult favorite for blackheads and rough texture, for people who already have a routine."},
            {"slug": "best-serum-face", "asin": "B01M4MCUAF", "titulo": "TruSkin Vitamin C Serum", "rating": 4.4, "reviews": 157154, "cat": "Serum",
             "motivo": "One of the most-rated vitamin C serums on Amazon (157,000+ ratings), for dull skin."},
            {"slug": "best-spf-50-face-sunscreen", "asin": "B002MSN3QQ", "titulo": "EltaMD UV Clear SPF 46", "rating": 4.5, "reviews": 71448, "cat": "Sunscreen",
             "motivo": "The face sunscreen dermatologists often suggest for acne-prone and red, sensitive skin."},
            {"slug": "best-spf-50-face-sunscreen", "asin": "B0GQVB7LH6", "titulo": "Supergoop! Unseen Sunscreen SPF 50", "rating": 4.6, "reviews": 19855, "cat": "Sunscreen",
             "motivo": "A clear gel that leaves no white cast on any skin tone and works as a makeup primer."},
        ],
    },
    {
        "slug": "christmas-gifts-for-home-cooks",
        "emoji": "🍳",
        "title": "Christmas Gifts for Home Cooks",
        "h1": "Christmas Gifts for Home Cooks: Air Fryers and Kitchen Upgrades",
        "desc": "Christmas gifts for home cooks: Ninja, COSORI, Instant Vortex and Chefman air fryers by household size, plus a Breville smart oven and a cold brew maker, from buyer ratings.",
        "intro": "An air fryer is one of the few kitchen gifts that gets used every week: it reheats, roasts and crisps faster than an oven. The trick is the size. A 2-quart model is perfect for one person and useless for a family of five, so each pick below says how many people it feeds.",
        "tips": [
            "Rough sizing: 2 qt for one person, 4 to 5 qt for two or three, 6 qt or a dual basket for families.",
            "Check counter space: larger and dual-basket models are wide.",
            "If they already own an air fryer, a smart countertop oven or a cold brew maker is a better upgrade.",
        ],
        "items": [
            {"slug": "best-air-fryer", "asin": "B07FDJMC9Q", "titulo": "Ninja AF101 Air Fryer (4 qt)", "rating": 4.7, "reviews": 59554, "cat": "Air fryer",
             "motivo": "The best overall pick for two to three people: simple, fast and easy to clean."},
            {"slug": "best-air-fryer", "asin": "B0CCJ8X596", "titulo": "COSORI Pro LE Air Fryer (5 qt)", "rating": 4.7, "reviews": 35901, "cat": "Air fryer",
             "motivo": "A mid-size model with a PFAS-free ceramic-coated basket."},
            {"slug": "best-air-fryer", "asin": "B07VHFMZHJ", "titulo": "Instant Vortex Plus Air Fryer (6 qt)", "rating": 4.5, "reviews": 81535, "cat": "Air fryer",
             "motivo": "The most popular large basket for families."},
            {"slug": "best-air-fryer", "asin": "B089TQWJKK", "titulo": "Ninja Foodi DualZone DZ201 (8 qt)", "rating": 4.8, "reviews": 25193, "cat": "Air fryer",
             "motivo": "Two baskets cook a main and a side at the same time and finish together; great for meal prep."},
            {"slug": "best-air-fryer", "asin": "B0DC11YH4J", "titulo": "Chefman 2-Quart Mini Air Fryer", "rating": 4.5, "reviews": 30250, "cat": "Air fryer",
             "motivo": "A small, low-cost air fryer for one person, a dorm or a small apartment."},
            ("best-breville-smart-oven-air-fryer", "A countertop oven that also air fries, for cooks who want one appliance instead of two.", "Breville Smart Oven Pro"),
            ("best-iced-coffee-maker-machine", "A cold brew maker for coffee lovers who drink iced coffee all year.", "VINCI Cold Brew Coffee Maker"),
        ],
    },
    {
        "slug": "christmas-gifts-for-new-parents",
        "emoji": "👶",
        "title": "Christmas Gifts for New Parents",
        "h1": "Christmas Gifts for New Parents: Baby Monitors and Everyday Helpers",
        "desc": "Christmas gifts for new parents: Infant Optics, HelloBaby and VTech baby monitors, the Owlet Dream Sock, a lightweight travel stroller and toddler toys, with notes on who each one suits.",
        "intro": "New parents need fewer cute outfits and more things that make nights and outings easier. A good baby monitor is the classic big gift; a light travel stroller and a toy that keeps a toddler busy are smaller ones that get used daily. Ask first: many parents already received a monitor at the baby shower.",
        "tips": [
            "No-WiFi monitors (Infant Optics, HelloBaby) are simpler and more private; WiFi ones add a phone app.",
            "Sleep-tracking devices like the Owlet are not a substitute for safe sleep practices; check with the parents first.",
            "Keep the gift receipt: duplicates are common with baby gear.",
        ],
        "items": [
            {"slug": "best-baby-monitor", "asin": "B08FF4GV5C", "titulo": "Infant Optics DXR-8 Pro", "rating": 4.6, "reviews": 7180, "cat": "Baby monitor",
             "motivo": "A no-WiFi monitor known for clear sound and privacy."},
            {"slug": "best-baby-monitor", "asin": "B09GM8JZM9", "titulo": "HelloBaby HB6550 Baby Monitor", "rating": 4.5, "reviews": 19915, "cat": "Baby monitor",
             "motivo": "The best-value no-WiFi monitor: simple to set up and easy on the budget."},
            {"slug": "best-baby-monitor", "asin": "B07WCV632L", "titulo": "VTech Smart WiFi Baby Monitor", "rating": 4.1, "reviews": 7644, "cat": "Baby monitor",
             "motivo": "A hybrid with a parent screen plus a phone app, for parents who want both."},
            {"slug": "best-baby-monitor", "asin": "B09NCGQSY9", "titulo": "Owlet Dream Sock", "rating": 4.0, "reviews": 5437, "cat": "Sleep tracker",
             "motivo": "For parents who specifically want sleep tracking; a big gift, so ask before buying."},
            ("best-stroller-lightweight", "A light travel stroller that folds small, for car trips and flights over the holidays.", "Lightweight Travel Stroller"),
            ("best-toddler-toys", "A light-up ramp toy that keeps toddlers busy, for families with an older sibling.", "Funwee 2-in-1 Rolling Ball and Car Ramp"),
        ],
    },
]

TIENDA = {"amazon": "Amazon", "ebay": "eBay"}
_IMG = Path(__file__).resolve().parent / "imagenes_asin.json"
IMAGENES = json.loads(_IMG.read_text(encoding="utf-8")) if _IMG.exists() else {}


# Some manifest categories are wrong (the board games page was filed under Pet Supplies)
CAT_FIX = {"best-family-board-games-for-vacation": "Toys & Games"}


def productos(items, manifest):
    """Merges each slug with its manifest data; skips missing pages and stores other than Amazon/eBay."""
    datos = {m["slug"]: m for m in manifest}
    out = []
    for it in items:
        if isinstance(it, dict):  # producto con datos verificados (páginas profundas): no depende del manifiesto
            if not (DOCS_DIR / it["slug"] / "index.html").exists():
                print(f"  SKIP {it['slug']} — page missing")
                continue
            img = re.sub(r"/images/W/[^/]+/images/", "/images/", IMAGENES.get(it["asin"], ""))
            out.append({"slug": it["slug"], "source": "amazon", "titulo": it["titulo"], "rating": it["rating"],
                        "reviews": it["reviews"], "imagen_url": img, "motivo": it["motivo"], "amazon_cat": it["cat"],
                        "affiliate_url": f"https://www.amazon.com/dp/{it['asin']}?tag=trendvortex00-20"})
            continue
        slug, motivo, *nombre = it
        m = datos.get(slug)
        if not m or m.get("source") not in TIENDA or not (DOCS_DIR / slug / "index.html").exists():
            print(f"  SKIP {slug} — not in manifest, store not supported, or page missing")
            continue
        out.append({**m, "motivo": motivo, **({"titulo": nombre[0]} if nombre else {}),
                    "amazon_cat": CAT_FIX.get(slug, m["amazon_cat"])})
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
    # eBay manifest entries carry placeholder ratings (4.2 / 50), so only Amazon ratings are shown
    amazon = [p for p in products if p["source"] == "amazon"]
    total_reviews = sum(p["reviews"] for p in amazon)
    tiendas = " and ".join(sorted({TIENDA[p["source"]] for p in products}))
    cards = ""
    for p in products:
        titulo = p["titulo"][:70] + ("..." if len(p["titulo"]) > 70 else "")
        meta = (f"""<span class="card-stars">{hub.stars(p['rating'])}</span>
          <span class="card-rating">{p['rating']}★</span>
          <span class="card-reviews">({p['reviews']:,} ratings)</span>""" if p["source"] == "amazon"
                else '<span class="card-reviews">Sold on eBay</span>')
        cards += f"""
    <div class="prod-card">
      <a href="{SITE_URL}/{p['slug']}/" class="card-img-link">
        <img src="{p['imagen_url']}" alt="{titulo}" loading="lazy">
      </a>
      <div class="card-body">
        <div class="card-cat">{p['amazon_cat']}</div>
        <a href="{SITE_URL}/{p['slug']}/" class="card-title">{titulo}</a>
        <div class="card-meta">
          {meta}
        </div>
        <p class="card-why">{p['motivo']}</p>
        <div class="card-actions">
          <a href="{SITE_URL}/{p['slug']}/" class="btn-review">Read Review →</a>
          <a href="{p['affiliate_url']}" class="btn-buy" rel="nofollow sponsored" target="_blank">Check Price on {TIENDA[p['source']]} →</a>
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
<link rel="icon" href="/favicon.ico">
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
  <p style="font-size:.78rem;color:var(--text3);margin-top:18px">Ratings were taken from Amazon when each review was written. Prices change often during the holiday season, so check the current price on {tiendas} before buying.</p>
</section>
</div>
<footer>
  <strong>Affiliate disclosure:</strong> TrendVortex.tech earns a commission from {tiendas} when you buy through our links, at no extra cost to you.<br>
  <span style="display:block;margin-top:.4rem">© {anio} TrendVortex.tech · <a href="{SITE_URL}">Home</a> · Updated {mes}</span>
<nav class="tv-site-links" aria-label="Site" style="margin-top:.5rem;font-size:.8rem"><a href="/about.html">About</a> · <a href="/affiliate-disclosure.html">Affiliate Disclosure</a> · <a href="/contact.html">Contact</a> · <a href="/privacy-policy.html">Privacy Policy</a></nav>
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
