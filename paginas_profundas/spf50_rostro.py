"""SPF 50 para el rostro (18-nov-2026). Fusiona best-sunscreen-for-face-spf-50 en best-spf-50-face-sunscreen.
Calificaciones y datos leídos en las fichas de Amazon el 18-nov-2026."""
from construir import construir, fusionar

F = "November 18, 2026"
C = dict(
    slug="best-spf-50-face-sunscreen", fecha=F,
    title="Best SPF 50 Sunscreen 2026: 6 Face Picks by Skin Type, Incl. No White Cast | TrendVortex",
    desc="Best SPF 50 face sunscreens compared by skin type: EltaMD UV Clear, La Roche-Posay Anthelios Mineral, Supergoop Unseen, ISDIN Eryfotona, CeraVe Mineral and Neutrogena Ultra Sheer, with filters, finish and who should skip each.",
    h1="Best SPF 50 Sunscreen for Face: 6 Picks by Skin Type",
    sub="The best face sunscreen is the one you will wear every day. We compared six popular high-SPF options by filter type, finish and skin type, using each listing's published ingredients and owner ratings.",
    eyebrow="Skincare", migas="Beauty",
    nota_tabla=f"Ratings and rating counts are those shown on Amazon on {F}. SPF, filters and size come from each product listing.",
    cols=["SPF", "Filter"],
    titulo_pasos="How to choose a face sunscreen in 4 questions",
    pasos=[
        ("Mineral or chemical filters?",
         "Mineral (zinc oxide, titanium dioxide) sits on the skin and is usually gentler for sensitive or reactive skin, but "
         "can leave a white cast. Chemical filters absorb UV and tend to look invisible on all skin tones. Both protect when "
         "applied correctly."),
        ("What is your skin type?",
         "Oily or acne-prone skin does best with oil-free, lightweight fluids or gels. Dry skin likes formulas with "
         "glycerin, ceramides or hyaluronic acid. Rosacea and very sensitive skin usually tolerate zinc-based mineral formulas best."),
        ("Do you want a tint?",
         "Tinted mineral sunscreens hide the white cast and add light coverage. They also contain iron oxides, which help "
         "against visible light, useful if you deal with dark spots or melasma."),
        ("Will you reapply?",
         "Sunscreen wears off. Reapply every 2 hours outdoors and after swimming or sweating. If you spend time in water, "
         "choose a water-resistant formula (40 or 80 minutes)."),
    ],
    productos=[
        dict(nombre="EltaMD UV Clear Broad-Spectrum SPF 46", asin="B002MSN3QQ", para="Best for acne-prone and rosacea-prone skin",
             extra=["46", "Mineral + chemical (zinc oxide)"], estrellas=4.5, n=71448,
             texto="UV Clear is the most-rated face sunscreen in this list by a wide margin. It is oil-free, contains zinc oxide "
                   "and niacinamide, and owners with breakouts and redness repeat the same comment: it does not clog pores. "
                   "It comes clear or tinted. Note that it is SPF 46, just under 50; in practice how much you apply matters more "
                   "than that difference.",
             saltar="you need a strict SPF 50 label or a fully mineral formula."),
        dict(nombre="La Roche-Posay Anthelios Mineral Light Fluid SPF 50", asin="B007U54P36", para="Best tinted mineral for sensitive skin",
             extra=["50", "100% mineral (titanium dioxide, zinc oxide)"], estrellas=4.4, n=33077,
             texto="A 100% mineral fluid that the brand formulates for sensitive skin. The tinted version blends into most "
                   "light-to-medium skin tones and removes the chalky look of mineral sunscreens; it is also oxybenzone-free "
                   "and oil-free, per the listing.",
             saltar="you have deep skin and the tint does not match, or you prefer a completely invisible gel."),
        dict(nombre="Supergoop! Unseen Sunscreen SPF 50", asin="B0GQVB7LH6", para="Best invisible finish for every skin tone",
             extra=["50", "Chemical"], estrellas=4.6, n=19855,
             texto="A clear, weightless gel that leaves no cast on any skin tone and doubles as a makeup primer. It is the "
                   "pick if you have tried mineral sunscreens and hated the look.",
             saltar="your skin reacts to chemical filters or you want a moisturizer and sunscreen in one."),
        dict(nombre="ISDIN Eryfotona Actinica SPF 50+", asin="B0CV8716J5", para="Best ultralight mineral for daily use",
             extra=["50+", "100% mineral (zinc oxide)"], estrellas=4.5, n=5807,
             texto="A very light zinc-oxide fluid that dermatologists often recommend for sun-damaged skin. It spreads easily "
                   "and owners report little or no white cast for a mineral formula.",
             saltar="you are on a tight budget: it is one of the pricier options per ounce."),
        dict(nombre="CeraVe 100% Mineral Sunscreen SPF 50", asin="B07KLY4RYG", para="Best for dry skin on a budget",
             extra=["50", "100% mineral (titanium dioxide 9%, zinc oxide 7%)"], estrellas=3.9, n=22125,
             texto="A hydrating mineral lotion with ceramides, niacinamide and hyaluronic acid, at a drugstore price. It has the "
                   "lowest rating here, and the reason is consistent: with 9% titanium dioxide it can leave a visible white cast, "
                   "especially on medium and deep skin.",
             saltar="you have medium or deep skin and do not want a white cast."),
        dict(nombre="Neutrogena Ultra Sheer Dry-Touch SPF 55", asin="B0GXR2V2YL", para="Best value for face and body, outdoors",
             extra=["55", "Chemical"], estrellas=4.6, n=17923,
             texto="The classic drugstore pick for days outside. It has a dry-touch finish, is water resistant for 80 minutes and "
                   "is oxybenzone-free, per the listing. A 3 oz bottle covers face and body, so the cost per use is low.",
             saltar="your face is very sensitive: a mineral face formula is gentler."),
    ],
    secciones=[
        ("What SPF 50 really means",
         "<p>SPF measures protection against UVB, the rays that cause sunburn. In lab conditions SPF 30 blocks about 97% of "
         "UVB and SPF 50 about 98%. The bigger difference in real life is the amount you apply: most people use a quarter to "
         "a half of the tested amount. For the face, a common guide is about a quarter teaspoon, or two finger-lengths of "
         "product. Always look for <strong>broad spectrum</strong> on the label, which means it also protects against UVA, "
         "the rays linked to skin aging.</p>"),
    ],
    faq=[
        ("Is SPF 50 better than SPF 30 for the face?",
         "Slightly. SPF 30 blocks about 97% of UVB and SPF 50 about 98%. SPF 50 helps more if you burn easily, have dark spots "
         "or spend long hours outdoors, but applying enough and reapplying matters more than the number."),
        ("Which sunscreen does not leave a white cast?",
         "Chemical sunscreens such as Supergoop! Unseen leave no cast. Among mineral options, tinted formulas like La Roche-Posay "
         "Anthelios Mineral Light Fluid and lightweight fluids like ISDIN Eryfotona leave the least."),
        ("What is the best sunscreen for acne-prone skin?",
         "Look for oil-free, non-comedogenic formulas. EltaMD UV Clear, with zinc oxide and niacinamide, is the most common "
         "choice among people with breakouts and redness."),
        ("Can I use body sunscreen on my face?",
         "You can, but body formulas are often thicker and more likely to sting the eyes or clog pores. If you use one, pick an "
         "oil-free, lightweight option such as a dry-touch lotion."),
        ("Do I need sunscreen indoors or on cloudy days?",
         "Most UVA passes through clouds and window glass. If you sit near windows or go outside during the day, daily "
         "sunscreen is worth it."),
        ("How long does sunscreen last after opening?",
         "Most sunscreens are made to stay effective for about three years if there is no expiration date. If it has an "
         "expiration date, follow it, and discard any sunscreen that changed color, smell or texture."),
    ],
    metodo="This guide is based on product listings, published ingredients and owner ratings; we did not lab-test SPF. "
           "Talk to a dermatologist if you have a skin condition.",
)

if __name__ == "__main__":
    construir(C)
    fusionar("best-sunscreen-for-face-spf-50", "best-spf-50-face-sunscreen")
