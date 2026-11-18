"""Serum para el rostro por objetivo (18-nov-2026). Fusiona best-best-serum-face en best-serum-face.
Calificaciones y datos leídos en las fichas de Amazon el 18-nov-2026."""
from construir import construir, fusionar

F = "November 18, 2026"
C = dict(
    slug="best-serum-face", fecha=F,
    title="Best Face Serums 2026: 6 Picks by Skin Goal, Pros and Cons | TrendVortex",
    desc="Best face serums compared by goal: niacinamide, retinol, vitamin C, hyaluronic acid and BHA. The Ordinary, CeraVe, TruSkin, Paula's Choice and Timeless, with pros, cons and who should skip each.",
    h1="Best Face Serums: 6 Picks by Skin Goal",
    sub="A serum is only as good as its active ingredient and how well it matches your skin. We grouped the most popular serums by what they actually do, with the pros, the cons and who should skip each one.",
    eyebrow="Skincare", migas="Beauty",
    nota_tabla=f"Ratings and rating counts are those shown on Amazon on {F}. Active ingredients come from each product listing.",
    cols=["Key active", "Use"],
    titulo_pasos="How to pick a serum in 4 steps",
    pasos=[
        ("Start from one goal, not five",
         "Pick the problem that bothers you most: breakouts and oil (niacinamide, BHA), texture and fine lines (retinol), "
         "dullness and dark spots (vitamin C) or dryness (hyaluronic acid). One well-chosen serum beats a crowded routine."),
        ("Match strength to your skin",
         "Higher percentages are not always better. A 20% vitamin C or a retinol can irritate sensitive skin. If you are new "
         "to an active, start with a gentle formula two or three times a week."),
        ("Know what not to combine",
         "Use retinol at night and vitamin C in the morning. Avoid stacking retinol and strong acids such as BHA on the same "
         "night when you are starting out. Niacinamide and hyaluronic acid pair well with almost everything."),
        ("Always finish with sunscreen",
         "Retinol, acids and vitamin C make the benefits of daily sunscreen even more important. See our "
         "<a href=\"/best-spf-50-face-sunscreen/\">SPF 50 face sunscreen guide</a>."),
    ],
    productos=[
        dict(nombre="The Ordinary Niacinamide 10% + Zinc 1%", asin="B0DDQ4MSXS", para="Best for oily, blemish-prone skin and pores",
             extra=["Niacinamide 10%, zinc 1%", "AM or PM"], estrellas=4.7, n=71311,
             texto="An inexpensive, simple serum for oil control, visible pores and post-blemish redness. It is one of the most "
                   "rated serums on Amazon. <strong>Pros:</strong> cheap, easy to layer, works with most routines. "
                   "<strong>Cons:</strong> some people find 10% niacinamide too strong and get redness or pilling under makeup.",
             saltar="your skin is very reactive: try a lower-strength niacinamide first."),
        dict(nombre="CeraVe Resurfacing Retinol Serum", asin="B07VWSN95S", para="Best first retinol for texture and post-acne marks",
             extra=["Encapsulated retinol, ceramides, niacinamide", "PM"], estrellas=4.6, n=57620,
             texto="A gentle entry into retinol. The listing describes encapsulated retinol plus three ceramides and niacinamide "
                   "to support the skin barrier, aimed at post-acne marks and rough texture. "
                   "<strong>Pros:</strong> beginner-friendly, fragrance-free, low price. <strong>Cons:</strong> slower results than "
                   "stronger retinoids; still causes some dryness at first.",
             saltar="you are pregnant or breastfeeding (ask your doctor about retinoids) or already use a prescription retinoid."),
        dict(nombre="TruSkin Vitamin C Serum", asin="B01M4MCUAF", para="Most popular vitamin C for dull skin",
             extra=["Vitamin C, vitamin E, hyaluronic acid", "AM"], estrellas=4.4, n=157154,
             texto="The most rated face serum in this guide by far. It combines vitamin C with vitamin E and hyaluronic acid "
                   "for a brighter look and some hydration. <strong>Pros:</strong> easy to use, affordable, lots of owner feedback. "
                   "<strong>Cons:</strong> the formula is less concentrated than pure 15 to 20% L-ascorbic acid serums, so changes "
                   "in dark spots are gradual.",
             saltar="you want the strongest vitamin C available: see Timeless below."),
        dict(nombre="The Ordinary Hyaluronic Acid 2% + B5 (with ceramides)", asin="B0DN6NG52J", para="Best for dry or dehydrated skin",
             extra=["Hyaluronic acid, vitamin B5, ceramides", "AM and PM"], estrellas=4.7, n=43880,
             texto="A hydrating serum that layers under any moisturizer and calms the dryness that retinol and acids can cause. "
                   "<strong>Pros:</strong> gentle, cheap, pairs with everything. <strong>Cons:</strong> it hydrates but does not "
                   "treat spots, acne or wrinkles by itself; apply on damp skin and seal with a moisturizer.",
             saltar="your main goal is acne, dark spots or fine lines."),
        dict(nombre="Paula's Choice Skin Perfecting 2% BHA Liquid Exfoliant", asin="B00949CTQQ", para="Best for blackheads and rough texture",
             extra=["Salicylic acid 2% (BHA)", "PM, 3 to 7 times a week"], estrellas=4.5, n=117275,
             texto="Technically a leave-on exfoliant rather than a serum, but it is the product most people mean when they ask "
                   "what smooths texture. Salicylic acid works inside the pore, which helps with blackheads and clogged pores. "
                   "<strong>Pros:</strong> visible results on texture, huge owner base. <strong>Cons:</strong> pricier per ounce; can "
                   "sting or dry the skin if used every day from the start.",
             saltar="you have very dry or eczema-prone skin, or you already use retinol nightly."),
        dict(nombre="Timeless 20% Vitamin C + E Ferulic Acid Serum", asin="B07NJ2ZNL1", para="Strongest vitamin C for dark spots and sun damage",
             extra=["L-ascorbic acid 20%, vitamin E, ferulic acid", "AM"], estrellas=4.3, n=14261,
             texto="A high-strength L-ascorbic acid serum with vitamin E and ferulic acid, a combination often compared with "
                   "far more expensive brands. <strong>Pros:</strong> strong formula for the price. <strong>Cons:</strong> it can "
                   "tingle or irritate sensitive skin, and pure vitamin C oxidizes: store it away from light and heat and stop "
                   "using it when it turns dark orange.",
             saltar="you have sensitive skin or rosacea: start with a gentler vitamin C."),
    ],
    secciones=[
        ("A simple routine that works",
         "<p><strong>Morning:</strong> gentle cleanser, vitamin C or niacinamide, moisturizer, sunscreen.<br>"
         "<strong>Night:</strong> cleanser, then retinol <em>or</em> BHA (alternate nights at first), hyaluronic acid if your "
         "skin feels tight, moisturizer.</p><p>Introduce one new active at a time and give it 6 to 12 weeks before you judge it. "
         "For a full routine by skin type see our <a href=\"/best-skin-care-routine/\">skin care routine guide</a>.</p>"),
    ],
    faq=[
        ("Which face serum is best for improving skin texture?",
         "For rough texture and clogged pores, a 2% BHA such as Paula's Choice works fastest. For texture plus fine lines "
         "and post-acne marks over time, a retinol such as CeraVe Resurfacing Retinol Serum is the usual choice."),
        ("Can I use vitamin C and retinol together?",
         "Yes, but not at the same time. Use vitamin C in the morning and retinol at night to reduce irritation."),
        ("Can I use niacinamide with vitamin C?",
         "Yes. Modern formulas can be layered. If your skin flushes, use them at different times of day."),
        ("How long do serums take to work?",
         "Hydration is immediate. Oil control and texture often improve in 4 to 8 weeks. Dark spots and fine lines usually "
         "need about 12 weeks of consistent use."),
        ("Do I need more than one serum?",
         "No. Most people do well with one targeted serum plus moisturizer and sunscreen. Add a second only when the first "
         "is part of your routine without irritation."),
        ("Are cheap serums as good as expensive ones?",
         "Often, yes. What matters is the active ingredient, its concentration and a stable formula. Several of the picks "
         "here cost a fraction of luxury brands with similar actives."),
    ],
    metodo="This guide is based on product listings, published ingredients and owner ratings; we did not test these "
           "products in a lab. See a dermatologist for persistent acne, melasma or skin conditions.",
)

if __name__ == "__main__":
    construir(C)
    fusionar("best-best-serum-face", "best-serum-face")
