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
