"""Freidoras de aire (18-nov-2026). Calificaciones y datos leídos en las fichas de Amazon el 18-nov-2026."""
from construir import construir

F = "November 18, 2026"
C = dict(
    slug="best-air-fryer", fecha=F,
    title="Best Air Fryer 2026: 5 Picks by Household Size | TrendVortex",
    desc="Best air fryers for 2026 compared by household size: Ninja AF101, COSORI Pro LE, Instant Vortex Plus, Ninja Foodi DualZone DZ201 and Chefman 2-quart, with capacity, functions, ratings and who should skip each.",
    h1="Best Air Fryer: 5 Picks by Household Size",
    sub="The right air fryer is mostly a question of size: too small and you cook in batches, too big and it wastes counter space. We compared five of the most-rated models by capacity, functions and what owners report.",
    eyebrow="Kitchen", migas="Home & Kitchen",
    nota_tabla=f"Ratings and rating counts are those shown on Amazon on {F}. Capacity and functions come from each listing.",
    cols=["Capacity", "Functions"],
    titulo_pasos="How to choose an air fryer in 4 questions",
    pasos=[
        ("How many people do you cook for?",
         "As a rough guide: 2 quarts for one person or snacks, 4 to 5 quarts for two to four people, 6 quarts or more, or a "
         "dual-basket model, for families and batch cooking."),
        ("Basket or oven style?",
         "Basket air fryers crisp faster and are easier to clean. Oven-style models with racks fit more flat food (toast, "
         "pizza) but usually crisp less evenly."),
        ("One basket or two?",
         "Two baskets let you cook a main and a side at different temperatures and finish them together. They take more "
         "counter space and cost more."),
        ("What about the coating?",
         "Most baskets are nonstick. If you prefer to avoid PFAS-based coatings, look for ceramic baskets such as the COSORI "
         "Pro LE, and always use wooden or silicone tools."),
    ],
    productos=[
        dict(nombre="Ninja AF101 Air Fryer (4 qt)", asin="B07FDJMC9Q", para="Best overall for 2 to 3 people",
             extra=["4 qt", "Air fry, roast, reheat, dehydrate"], estrellas=4.7, n=59554,
             texto="A simple, proven basket fryer: 1550 W, a 105 to 400 °F range per the listing and a ceramic-coated nonstick "
                   "basket. Owners repeat that it cooks fast and evenly for its size, and the low temperature setting makes it "
                   "usable for dehydrating.",
             saltar="you regularly cook for four or more: choose a 6-quart or dual-basket model."),
        dict(nombre="COSORI Pro LE Air Fryer (5 qt)", asin="B0CCJ8X596", para="Best mid-size, with a PFAS-free ceramic basket",
             extra=["5 qt", "9-in-1"], estrellas=4.7, n=35901,
             texto="A compact 5-quart model with a PFAS-free ceramic basket and nine presets, reaching 450 °F for extra crisping. "
                   "It fits most kitchens and handles a meal for two to four people.",
             saltar="you need to cook two foods at once."),
        dict(nombre="Instant Vortex Plus Air Fryer (6 qt)", asin="B07VHFMZHJ", para="Most popular large basket for families",
             extra=["6 qt", "6-in-1"], estrellas=4.5, n=81535,
             texto="The most-rated air fryer in this guide. A 6-quart basket fits a whole meal for a family of four, and the "
                   "EvenCrisp airflow is designed to brown food on all sides with little oil.",
             saltar="counter space is tight: it is noticeably bigger than 4 to 5 quart models."),
        dict(nombre="Ninja Foodi DualZone DZ201 (8 qt)", asin="B089TQWJKK", para="Best dual-basket for families and meal prep",
             extra=["8 qt (2 × 4 qt)", "6-in-1"], estrellas=4.8, n=25193,
             texto="Two independent 4-quart baskets, so you can cook chicken in one and fries in the other and have them finish "
                   "at the same time. It has the highest rating in this guide.",
             saltar="you cook small portions: a single basket heats up and cleans up faster."),
        dict(nombre="Chefman 2-Quart Mini Air Fryer", asin="B0DC11YH4J", para="Best small air fryer for one person or dorms",
             extra=["2 qt", "Air fry"], estrellas=4.5, n=30250,
             texto="A compact, inexpensive fryer for one person, snacks and reheating, with a footprint that fits small "
                   "kitchens and dorm rooms.",
             saltar="you cook for two or more: you will end up cooking in batches."),
    ],
    secciones=[
        ("Air fryer tips that make a real difference",
         "<ul><li>Do not overfill the basket: a single layer crisps; a pile steams.</li>"
         "<li>Shake or flip halfway through cooking.</li>"
         "<li>Use a light spray or brush of oil for browning; skip aerosol sprays that can damage nonstick coatings.</li>"
         "<li>Preheat 3 to 5 minutes for frozen foods.</li>"
         "<li>Clean the basket after each use so grease does not smoke next time.</li></ul>"),
    ],
    faq=[
        ("What size air fryer do I need?",
         "About 2 quarts for one person, 4 to 5 quarts for two to four people and 6 quarts or a dual-basket model for "
         "families or batch cooking."),
        ("Is an air fryer healthier than deep frying?",
         "It uses far less oil, so most fried foods have less fat and fewer calories when air-fried. It is still a way of "
         "cooking, not a diet: what you cook matters most."),
        ("Do air fryers use a lot of electricity?",
         "Most draw about 1,200 to 1,700 W, but they cook faster than an oven and heat a small space, so a typical session "
         "often uses less energy than heating a full oven."),
        ("Can I put aluminum foil or parchment in an air fryer?",
         "Yes, if it is weighed down by food and does not block the airflow. Perforated parchment liners made for air fryers "
         "are the safer option."),
        ("Single or dual basket?",
         "Choose dual if you often cook a main and a side together. Choose single if you mostly cook one food or have little "
         "counter space."),
    ],
    metodo="This guide is based on product listings, published specifications and owner ratings; we did not lab-test "
           "these air fryers.",
)

if __name__ == "__main__":
    construir(C)
