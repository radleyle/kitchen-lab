"""Keyword-based detection of the FDA's nine major allergens.

Limitation (always surfaced to users): detection works on ingredient NAMES.
It cannot catch cross-contact, "may contain" risks, or unlisted ingredients
in packaged foods.
"""

# allergen -> ingredient keywords that imply it.
ALLERGEN_KEYWORDS: dict[str, list[str]] = {
    "milk": ["milk", "butter", "cream", "cheese", "yogurt", "whey", "casein",
             "ghee", "buttermilk", "custard", "ice cream"],
    "eggs": ["egg", "mayonnaise", "mayo", "meringue", "aioli"],
    "fish": ["fish", "salmon", "tuna", "cod", "anchovy", "tilapia", "halibut",
             "worcestershire", "fish sauce", "dashi", "bonito"],
    "crustacean_shellfish": ["shrimp", "prawn", "crab", "lobster", "crawfish",
                             "shrimp paste"],
    "tree_nuts": ["almond", "cashew", "walnut", "pecan", "pistachio",
                  "hazelnut", "macadamia", "brazil nut", "pine nut", "praline"],
    "peanuts": ["peanut", "groundnut"],
    "wheat": ["wheat", "flour", "bread", "breadcrumb", "panko", "pasta",
              "noodle", "seitan", "soy sauce", "couscous", "semolina"],
    "soybeans": ["soy", "soybean", "tofu", "edamame", "miso", "tempeh",
                 "soy sauce", "tamari"],
    "sesame": ["sesame", "tahini", "benne"],
}

# Keywords that LOOK like an allergen but aren't. Longer phrases first:
# "buckwheat flour" must be stripped whole, or removing just "buckwheat"
# would leave "flour" behind and wrongly flag wheat.
FALSE_FRIENDS: dict[str, list[str]] = {
    "milk": ["coconut milk", "oat milk", "almond milk", "soy milk", "rice milk"],
    "wheat": ["buckwheat flour", "buckwheat", "rice flour", "almond flour",
              "coconut flour", "chickpea flour", "cornflour", "corn flour",
              "gluten-free"],
    "eggs": ["eggplant"],
}


def detect_allergens(ingredients: list[str]) -> dict:
    """Return {allergen: [ingredients that triggered it]} plus the caveat."""
    found: dict[str, list[str]] = {}

    for raw in ingredients:
        ing = raw.lower().strip()
        for allergen, keywords in ALLERGEN_KEYWORDS.items():
            exceptions = FALSE_FRIENDS.get(allergen, [])
            # Skip if the ingredient is a known false friend ("almond milk"
            # is not dairy) -- unless a real trigger also appears.
            cleaned = ing
            for exc in exceptions:
                cleaned = cleaned.replace(exc, "")
            if any(kw in cleaned for kw in keywords):
                found.setdefault(allergen, []).append(raw)

    return {
        "allergens_detected": found,
        "note": (
            "Detected from ingredient names only. Cannot account for "
            "cross-contact or unlisted ingredients in packaged foods."
        ),
    }
