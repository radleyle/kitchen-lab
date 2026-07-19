"""Seed scientific mechanisms and the technique library.

Run inside the container:
    docker compose exec backend python -m app.seeds.techniques_seed

Additively idempotent on slug.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import ScientificMechanism, Technique

# slug, name, explanation
MECHANISMS = [
    ("maillard-browning", "Maillard browning",
     "Amino acids and reducing sugars react above roughly 140C to form "
     "brown pigments and hundreds of flavor compounds. Needs a dry surface "
     "and heat well above boiling."),
    ("protein-denaturation", "Protein denaturation and coagulation",
     "Heat unfolds muscle proteins; at higher temperatures they bond and "
     "squeeze out water. Tenderness and juiciness peak in a narrow window."),
    ("starch-gelatinization", "Starch gelatinization",
     "Starch granules absorb water and swell as they heat (roughly 60-95C "
     "depending on the starch), thickening liquids. Prolonged boiling or "
     "acid can break the network down."),
    ("emulsification", "Emulsification",
     "Tiny fat droplets stay suspended in water (or vice versa) when coated "
     "by an emulsifier such as egg yolk lecithin. Heat, rapid fat addition, "
     "or too little emulsifier collapses the emulsion."),
    ("osmosis-diffusion", "Osmosis and salt diffusion",
     "Salt dissolves and moves into meat along concentration gradients. "
     "It dissolves some muscle proteins so they hold more water during cooking."),
    ("leavening-gas", "Chemical and biological leavening",
     "Gas (CO2 from yeast or baking powder/soda reactions) inflates a "
     "gluten or egg-foam network; heat sets the structure before the gas escapes."),
    ("alkalinity-tenderizing", "Surface alkalinity (velveting)",
     "A brief alkaline treatment (baking soda) raises surface pH, reducing "
     "protein bonding so thin slices stay tender under high heat."),
    ("evaporation-concentration", "Evaporation and concentration",
     "Simmering drives off water, concentrating dissolved flavor compounds "
     "and thickening sauces. Too hard a boil can make reductions bitter or "
     "reduce past the useful point."),
    ("fat-soluble-flavor", "Fat-soluble flavor extraction",
     "Many spice and aromatic compounds dissolve better in fat than water. "
     "Gently heating spices in oil (blooming) releases aroma before liquid "
     "is added."),
]

# slug, name, summary, procedure, mistakes, foods, mechanism_slug
TECHNIQUES = [
    ("velveting", "Velveting",
     "A brief baking-soda (or cornstarch/egg white) marinade that keeps "
     "thin-sliced meat tender in a hot wok or skillet.",
     [
         "Slice meat thin against the grain.",
         "Toss with ~1/4 tsp baking soda per pound; rest 15-20 minutes.",
         "Rinse thoroughly and pat dry (skipping the rinse leaves a soapy taste).",
         "Optional: light cornstarch coat, then stir-fry hot and fast.",
     ],
     [
         "Using too much baking soda or skipping the rinse.",
         "Applying to thick steaks (meant for thin slices).",
         "Overcrowding the pan so meat steams instead of searing.",
     ],
     ["chicken breast", "beef for stir-fry", "pork loin slices"],
     "alkalinity-tenderizing"),
    ("dry-brining", "Dry brining (pre-salting)",
     "Salting meat ahead of time so salt dissolves some proteins and the "
     "meat retains more juice when cooked.",
     [
         "Pat meat dry.",
         "Salt evenly (roughly 0.5-1% of meat weight in salt).",
         "Rest uncovered in the fridge 40 minutes to overnight depending on thickness.",
         "Cook; do not rinse (the surface will re-dry for better browning).",
     ],
     [
         "Under-salting then adding more at the table inconsistently.",
         "Wet brining and dry brining the same piece (oversalts).",
     ],
     ["chicken", "turkey", "steak", "pork chops"],
     "osmosis-diffusion"),
    ("pan-searing", "Pan searing",
     "High-heat contact browning that builds a crust via the Maillard "
     "reaction while finishing to a safe/internal target.",
     [
         "Pat food very dry; salt ahead if dry-brining.",
         "Preheat a heavy pan until oil shimmers.",
         "Don't crowd; leave space so steam can escape.",
         "Leave undisturbed until a crust forms; flip once.",
         "Finish to temperature with a thermometer, then rest.",
     ],
     [
         "Wet surface or crowded pan -> gray steamed meat.",
         "Flipping constantly before a crust forms.",
         "Judging doneness by color alone.",
     ],
     ["steak", "chicken thighs", "fish fillets", "scallops"],
     "maillard-browning"),
    ("emulsion-sauce", "Emulsified butter/oil sauce",
     "Slowly incorporating fat into an emulsifier-rich base (yolk, mustard) "
     "so the sauce stays creamy instead of splitting into grease.",
     [
         "Start with a room-temp emulsifier base (yolk, mustard, or reduction).",
         "Add fat gradually while whisking constantly.",
         "Keep below a simmer; rescue a break with a spoon of warm water "
         "whisked into a fresh yolk, then slowly re-add the broken sauce.",
     ],
     [
         "Dumping fat in all at once.",
         "Boiling the sauce.",
         "Too much fat for the emulsifier present.",
     ],
     ["hollandaise", "mayonnaise", "pan sauces", "vinaigrettes"],
     "emulsification"),
    ("slurry-thickening", "Starch slurry thickening",
     "Mixing starch with cold liquid, then heating so granules gelatinize "
     "and thicken a sauce or gravy.",
     [
         "Whisk starch into cold water or stock (never dump dry into hot liquid).",
         "Stir into the simmering sauce.",
         "Bring just to a simmer until thickened; avoid long hard boils "
         "after thickening (especially with potato starch/arrowroot).",
     ],
     [
         "Adding dry starch directly -> lumps.",
         "Using cornstarch then boiling forever -> thins again.",
         "Arrowroot in dairy -> slimy texture.",
     ],
     ["gravy", "stir-fry sauce", "pie filling", "soup"],
     "starch-gelatinization"),
    ("creaming-method", "Creaming method (cookies/cakes)",
     "Beating solid fat with sugar to trap air that later expands in the "
     "oven, giving lift and a tender crumb.",
     [
         "Start with soft (not melted) butter.",
         "Beat with sugar until light and fluffy.",
         "Add eggs gradually, then dry ingredients just until combined.",
     ],
     [
         "Melted butter (no air pockets; cookies spread flat).",
         "Overmixing after flour (tough gluten).",
     ],
     ["cookies", "butter cakes", "some muffins"],
     "leavening-gas"),
    ("blanching", "Blanching",
     "A brief boil (then ice bath) that sets color, loosens skins, or "
     "partially cooks vegetables before finishing another way.",
     [
         "Bring a large pot of salted water to a rolling boil.",
         "Add food in batches so the water returns to a boil quickly.",
         "Cook briefly (often 30 seconds–3 minutes depending on the food).",
         "Shock in ice water to stop cooking; drain and dry well.",
     ],
     [
         "Crowding the pot so water goes lukewarm.",
         "Skipping the ice bath — food keeps cooking and turns dull.",
         "Under-salting the water for green vegetables.",
     ],
     ["green beans", "broccoli", "tomatoes (for peeling)", "nuts"],
     "protein-denaturation"),
    ("deglazing", "Deglazing",
     "Adding liquid to a hot pan to dissolve browned bits (fond) into a "
     "flavorful sauce base after searing.",
     [
         "After searing, pour off excess fat if needed; keep the browned bits.",
         "Add wine, stock, or water while the pan is still hot.",
         "Scrape the fond loose with a wooden spoon as the liquid simmers.",
         "Reduce to concentrate, then finish with butter, mustard, or cream.",
     ],
     [
         "Using a nonstick pan with no fond to dissolve.",
         "Adding cold liquid to a scorched (burned-black) pan — bitter sauce.",
         "Forgetting to reduce; watery, thin flavor.",
     ],
     ["pan sauces", "steak", "chicken", "pork chops"],
     "evaporation-concentration"),
    ("blooming-spices", "Blooming spices in fat",
     "Gently frying ground or whole spices in oil or ghee so fat-soluble "
     "aromas bloom before you add watery ingredients.",
     [
         "Heat a spoonful of oil or ghee over medium-low.",
         "Add spices (and optional aromatics like garlic/ginger).",
         "Stir 20–60 seconds until fragrant — not smoking or blackened.",
         "Add onions, tomatoes, or liquid to stop the toasting.",
     ],
     [
         "Burning spices on high heat (bitter, acrid).",
         "Adding spices straight into a watery stew first — muted aroma.",
     ],
     ["curries", "chili", "sofrito-style bases", "tempered dals"],
     "fat-soluble-flavor"),
    ("tempering-eggs", "Tempering eggs for custards",
     "Slowly warming beaten eggs with hot liquid so they thicken a sauce "
     "or custard without scrambling.",
     [
         "Whisk eggs (or yolks) in a bowl.",
         "Ladle a little hot milk/stock into the eggs while whisking.",
         "Repeat until the egg mix is warm, then return everything to the pot.",
         "Cook gently, stirring, until it coats a spoon; do not boil.",
     ],
     [
         "Dumping cold eggs into boiling liquid — scrambled bits.",
         "Boiling after combining — curdled custard.",
     ],
     ["pastry cream", "ice cream base", "avgolemono", "carbonara-style sauces"],
     "protein-denaturation"),
    ("resting-meat", "Resting meat after cooking",
     "Letting cooked meat sit so juices redistribute and carryover heat "
     "finishes the center gently.",
     [
         "Pull meat a few degrees under your final target if carryover is expected.",
         "Tent loosely with foil (or leave uncovered for a crisp crust).",
         "Rest: ~5 minutes for steaks/chops, 15–30 for large roasts.",
         "Slice against the grain just before serving.",
     ],
     [
         "Slicing immediately — juices flood the cutting board.",
         "Wrapping tightly in foil for ages — steamed, soggy crust.",
     ],
     ["steak", "roast chicken", "pork loin", "lamb"],
     "protein-denaturation"),
    ("reduction", "Sauce reduction",
     "Simmering a liquid uncovered so water evaporates and flavor "
     "concentrates into a glossy, clingy sauce.",
     [
         "Start with stock, wine, or pan juices in a wide pan (more surface = faster).",
         "Simmer gently, not a furious boil.",
         "Taste as it thickens; stop when flavor is intense but not salty-bitter.",
         "Finish off heat with cold butter or oil for shine if desired.",
     ],
     [
         "Reducing so far it tastes harsh or overly salty.",
         "Covering the pan — steam can’t escape, so it won’t reduce.",
     ],
     ["pan sauces", "demi-glace style bases", "glazes", "soups"],
     "evaporation-concentration"),
    ("folding-whites", "Folding whipped egg whites",
     "Gently combining airy foam into a heavier batter so you keep lift "
     "instead of knocking the gas out.",
     [
         "Whip whites to soft or stiff peaks as the recipe requires.",
         "Stir a spoonful of foam into the batter to loosen it.",
         "Add the rest; cut down through the middle, scrape the bowl, and fold over.",
         "Stop as soon as streaks mostly disappear — a few white streaks are fine.",
     ],
     [
         "Stirring or beating vigorously — deflates the foam.",
         "Overfolding until the batter looks soup-thin.",
     ],
     ["soufflés", "chiffon cake", "mousse", "some pancakes"],
     "leavening-gas"),
    ("breading-dredging", "Breading / dredging",
     "Building a dry–wet–dry coat so crumbs stick and fry into a crisp crust.",
     [
         "Pat food dry.",
         "Dust in flour (shake off excess).",
         "Dip in beaten egg or buttermilk.",
         "Press into breadcrumbs or seasoned flour; rest a few minutes so the coat sets.",
         "Fry or bake; don’t flip until the crust releases cleanly.",
     ],
     [
         "Skipping the flour step — egg slides off.",
         "Soggy crumbs from wet food or oil that isn’t hot enough.",
     ],
     ["cutlets", "fried chicken", "fish fillets", "onion rings"],
     "maillard-browning"),
]


def run(db: Session) -> str:
    mechanisms: dict[str, ScientificMechanism] = {}
    for slug, name, explanation in MECHANISMS:
        m = db.scalar(
            select(ScientificMechanism).where(ScientificMechanism.slug == slug)
        )
        if m is None:
            m = ScientificMechanism(slug=slug, name=name, explanation=explanation)
            db.add(m)
            db.flush()
        mechanisms[slug] = m

    added = 0
    for slug, name, summary, procedure, mistakes, foods, mech_slug in TECHNIQUES:
        exists = db.scalar(select(Technique).where(Technique.slug == slug))
        if exists is not None:
            continue
        db.add(
            Technique(
                slug=slug,
                name=name,
                summary=summary,
                procedure=procedure,
                common_mistakes=mistakes,
                applicable_foods=foods,
                mechanism_id=mechanisms[mech_slug].id,
            )
        )
        added += 1
    db.commit()
    return (
        f"Mechanisms: {len(mechanisms)}, new techniques: {added} "
        f"({len(TECHNIQUES)} in seed file)."
    )


if __name__ == "__main__":
    with SessionLocal() as session:
        print(run(session))
