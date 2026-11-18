"""Rutina de skin care por tipo de piel (18-nov-2026). Calificaciones de Amazon leídas el 18-nov-2026."""
from construir import construir

F = "November 18, 2026"
C = dict(
    slug="best-skin-care-routine", fecha=F,
    title="Best Skin Care Routine 2026: Simple Steps and Products by Skin Type | TrendVortex",
    desc="A simple, dermatologist-style skin care routine for 2026: cleanser, serum, moisturizer and sunscreen, with product picks for oily, dry, sensitive and combination skin.",
    h1="Best Skin Care Routine for 2026: 4 Steps by Skin Type",
    sub="A good routine is short: cleanse, treat, moisturize, protect. Below is the order that works, what to change for your skin type and well-rated products for each step.",
    eyebrow="Skincare", migas="Beauty",
    nota_tabla=f"Ratings and rating counts are those shown on Amazon on {F}.",
    cols=["Step", "Skin type"],
    titulo_pasos="The 4-step routine (morning and night)",
    pasos=[
        ("Cleanse",
         "Use a gentle cleanser morning and night. Squeaky-clean skin means the cleanser is too harsh. In the morning, "
         "dry or sensitive skin can simply rinse with water."),
        ("Treat (optional, one active at a time)",
         "This is where a serum goes: niacinamide or BHA for oil and pores, vitamin C for dullness, retinol at night for "
         "texture and fine lines. See our <a href=\"/best-serum-face/\">face serum guide</a> to pick one."),
        ("Moisturize",
         "Every skin type needs a moisturizer, including oily skin. Gel textures suit oily skin; creams with ceramides "
         "suit dry skin."),
        ("Protect (morning)",
         "Finish every morning with broad-spectrum sunscreen, SPF 30 or higher. It is the step with the strongest evidence "
         "against early aging and dark spots. Compare options in our <a href=\"/best-spf-50-face-sunscreen/\">SPF 50 face sunscreen guide</a>."),
    ],
    productos=[
        dict(nombre="CeraVe Hydrating Facial Cleanser", asin="B07RL88DD2", para="Best cleanser for normal to dry skin",
             extra=["1. Cleanse", "Normal, dry"], estrellas=4.7, n=133678,
             texto="A non-foaming lotion cleanser with ceramides and hyaluronic acid that removes sunscreen and dirt without "
                   "leaving the skin tight.",
             saltar="you wear heavy makeup (use a cleansing balm first) or your skin is very oily."),
        dict(nombre="CeraVe Foaming Facial Cleanser", asin="B07RJ18VMF", para="Best cleanser for oily and acne-prone skin",
             extra=["1. Cleanse", "Oily, combination"], estrellas=4.8, n=105444,
             texto="A gel that foams lightly and removes excess oil, made for normal to oily skin, with ceramides and niacinamide "
                   "so it is less stripping than classic foaming washes.",
             saltar="your skin is dry or easily irritated."),
        dict(nombre="Vanicream Gentle Facial Cleanser", asin="B09Y2JCYNK", para="Best cleanser for sensitive skin",
             extra=["1. Cleanse", "Sensitive, reactive"], estrellas=4.7, n=36065,
             texto="A minimalist, fragrance-free cleanser often suggested for skin that reacts to almost everything, including "
                   "people using prescription acne treatments.",
             saltar="you need a cleanser that removes waterproof makeup on its own."),
        dict(nombre="CeraVe Moisturizing Cream", asin="B00TTD9BRC", para="Best moisturizer for dry skin (face and body)",
             extra=["3. Moisturize", "Dry, very dry"], estrellas=4.7, n=149766,
             texto="A rich, fragrance-free cream with ceramides and hyaluronic acid. One tub covers face and body, which makes it "
                   "one of the best values in skin care.",
             saltar="your skin is oily: the texture can feel heavy on the face."),
        dict(nombre="Neutrogena Hydro Boost Water Gel", asin="B00NR1YQHM", para="Best moisturizer for oily and combination skin",
             extra=["3. Moisturize", "Oily, combination"], estrellas=4.6, n=88265,
             texto="A light water-gel with hyaluronic acid that hydrates without a greasy film and works well under makeup and "
                   "sunscreen.",
             saltar="your skin is sensitive to fragrance: check the version, as some owners mention a scent."),
        dict(nombre="EltaMD UV Clear SPF 46", asin="B002MSN3QQ", para="Best daily sunscreen for acne-prone skin",
             extra=["4. Protect", "All, especially acne-prone"], estrellas=4.5, n=71448,
             texto="Oil-free, with zinc oxide and niacinamide, and the most rated face sunscreen we compared. A reliable last "
                   "step every morning.",
             saltar="you need a fully mineral or a strict SPF 50 product: see the sunscreen guide for alternatives."),
    ],
    secciones=[
        ("Routine by skin type",
         "<p><strong>Oily or acne-prone:</strong> foaming cleanser, niacinamide or 2% BHA (at night, a few times a week), "
         "water-gel moisturizer, oil-free sunscreen.</p>"
         "<p><strong>Dry:</strong> hydrating cleanser at night and water in the morning, hyaluronic acid on damp skin, "
         "ceramide cream, a moisturizing sunscreen.</p>"
         "<p><strong>Sensitive:</strong> minimalist cleanser, skip actives for the first two weeks, fragrance-free moisturizer, "
         "mineral sunscreen. Add one active at a time.</p>"
         "<p><strong>Combination:</strong> gentle cleanser, light gel moisturizer all over and a richer cream only on dry "
         "areas, oil-free sunscreen.</p>"),
        ("Mistakes that ruin a good routine",
         "<ul><li>Using several strong actives at once (retinol, acids and vitamin C on the same night).</li>"
         "<li>Skipping moisturizer because the skin is oily.</li>"
         "<li>Applying too little sunscreen, or none on cloudy days.</li>"
         "<li>Changing products every week. Give each product 6 to 12 weeks.</li></ul>"),
    ],
    faq=[
        ("What is the correct order of a skin care routine?",
         "From thinnest to thickest: cleanser, toner if you use one, serum, moisturizer and, in the morning, sunscreen last."),
        ("What is the simplest skin care routine?",
         "Cleanser, moisturizer and sunscreen in the morning; cleanser and moisturizer at night. Add a serum only for a "
         "specific goal."),
        ("Do I need a different routine at night?",
         "Yes. Skip sunscreen at night and use that time for retinol or exfoliating acids, which work better without sun exposure."),
        ("How long before a new routine shows results?",
         "Hydration improves within days. Breakouts and texture usually take 4 to 8 weeks, dark spots about 12 weeks."),
        ("Are drugstore products good enough?",
         "Yes. The cleansers, moisturizers and sunscreens in this guide are drugstore or mid-priced and are among the most "
         "rated in their category."),
    ],
    metodo="This guide is based on product listings, published ingredients and owner ratings. It is general information, "
           "not medical advice; see a dermatologist for acne that does not improve, rosacea or eczema.",
)

if __name__ == "__main__":
    construir(C)
