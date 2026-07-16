"""Seed the diagnosis taxonomy: symptoms and their weighted causes.

Run inside the container:
    docker compose exec backend python -m app.seeds.symptoms_seed

Additively idempotent (skips existing symptom slugs).

prior_weight = how common this cause is BEFORE any evidence, 0-1.
Weights within a symptom need not sum to 1; scoring normalizes them.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Symptom, SymptomCause

# slug, description, domain, causes: (cause, explanation, prior, follow_up)
SYMPTOMS = [
    ("meat-tough-dry", "Meat came out tough, dry, or chewy", "meat", [
        ("Overcooked past target temperature",
         "Above ~60C muscle proteins contract and squeeze out moisture; every "
         "extra degree costs juiciness. The most common cause by far.",
         0.5,
         "Did you use a thermometer? Roughly how long did it cook and at what heat?"),
        ("Sliced with the grain instead of against it",
         "Long intact muscle fibers chew tough even when perfectly cooked.",
         0.2,
         "When you sliced it, did you cut across the visible lines of the meat or along them?"),
        ("Cut unsuited to the cooking method",
         "Lean tender cuts dry out in long cooking; collagen-rich cuts stay "
         "tough in fast cooking -- they need hours to convert collagen to gelatin.",
         0.2,
         "What cut was it, and was it a quick sear or a long cook?"),
        ("No pre-salting or brining",
         "Salting ahead helps proteins retain water during cooking; skipping "
         "it lowers the margin for error.",
         0.1,
         "Did you salt the meat ahead of time, right before cooking, or after?"),
    ]),
    ("sauce-broken", "Emulsified sauce separated / broke into grease", "sauces", [
        ("Fat added too quickly",
         "Droplets merge faster than the emulsifier can coat them; the "
         "emulsion collapses into grease.",
         0.4,
         "How did you add the butter/oil -- gradually while whisking, or in large additions?"),
        ("Overheated the emulsion",
         "Heat thins the emulsifier layer and speeds droplet collisions; "
         "butter sauces break readily near a simmer.",
         0.35,
         "How hot did the sauce get -- did it ever bubble or simmer?"),
        ("Not enough emulsifier for the fat",
         "Every emulsion has a fat capacity for its emulsifier; exceeding it "
         "breaks the sauce even with perfect technique.",
         0.25,
         "Roughly how much fat did you use per yolk (or per spoonful of mustard/base)?"),
    ]),
    ("sauce-thin", "Sauce or gravy stayed thin / got watery", "sauces", [
        ("Not enough starch for the liquid",
         "Thickening scales with starch concentration; under-dosing gives a "
         "thin result no matter the technique.",
         0.35,
         "Roughly how much starch did you use per cup of liquid?"),
        ("Starch never reached gelatinization temperature",
         "Starch only thickens once granules swell, roughly 60-95C depending "
         "on the starch; a sauce kept too cool never thickens.",
         0.25,
         "Did the sauce come up to a visible simmer after you added the starch?"),
        ("Prolonged boiling or stirring broke the starch down",
         "After thickening, extended boiling or vigorous stirring ruptures "
         "the swollen granules and the sauce thins irreversibly.",
         0.25,
         "After it thickened, did it keep boiling or get stirred hard for a while?"),
        ("Acidic ingredients weakened the gel",
         "Strong acid hydrolyzes starch during long cooking, reducing its "
         "thickening power.",
         0.15,
         "Does the sauce contain a lot of acid (citrus, vinegar, wine) added early?"),
    ]),
    ("no-browning", "Food won't brown / turns gray and steams", "meat", [
        ("Surface too wet",
         "Evaporating water pins the surface near 100C, well below browning "
         "temperatures; browning waits until the surface dries.",
         0.35,
         "Did you pat the food dry before it hit the pan?"),
        ("Pan overcrowded",
         "Many cold pieces release steam faster than it can escape and drop "
         "the pan temperature; food stews instead of searing.",
         0.3,
         "How full was the pan -- pieces touching each other or spaced out?"),
        ("Heat too low",
         "Browning reactions need surface temperatures well above boiling; a "
         "moderate pan never gets there in reasonable time.",
         0.25,
         "Was the pan fully preheated, and did the food sizzle hard on contact?"),
        ("Moved / flipped too early and often",
         "Constant movement resets surface contact and releases juices, "
         "interrupting crust formation.",
         0.1,
         "Did you leave it undisturbed for the first minutes, or move it around?"),
    ]),
    ("cookies-spread", "Cookies spread flat and thin", "baking", [
        ("Butter too warm or melted",
         "Fat that liquefies before the structure sets lets the dough slump "
         "and spread across the pan.",
         0.4,
         "Was the butter softened/melted, and was the dough warm when it went in the oven?"),
        ("No chilling before baking",
         "Chilled dough spreads less: the fat starts solid and flour is fully "
         "hydrated.",
         0.25,
         "Did the dough get chilled before baking, and for how long?"),
        ("Too much sugar or too little flour",
         "Sugar liquefies as it melts and excess of it (or scant flour) thins "
         "the dough; measuring flour by volume commonly under-doses it.",
         0.25,
         "Did you measure flour by weight or by cups? Any recipe changes to sugar?"),
        ("Warm baking sheets between batches",
         "Dough on a hot-from-the-oven sheet starts melting and spreading "
         "before it even bakes.",
         0.1,
         "Were later batches placed on sheets still warm from the previous batch?"),
    ]),
    ("bread-dense", "Bread baked up dense and heavy", "baking", [
        ("Under-proofed dough",
         "Insufficient fermentation means too little gas; the crumb sets "
         "tight and heavy.",
         0.35,
         "How long did it rise, at what room temperature, and did it clearly grow before baking?"),
        ("Weak gluten development",
         "Without enough kneading/time/hydration the gluten network cannot "
         "hold the gas that is produced.",
         0.3,
         "How was the dough worked -- kneaded until springy, or mixed briefly?"),
        ("Too much flour / dough too dry",
         "Stiff, dry dough resists expansion; volume-measured flour often "
         "overshoots by 20-30%.",
         0.25,
         "Did you measure flour by weight or by cups, and did the dough feel stiff?"),
        ("Yeast dead or expired",
         "Old yeast or yeast killed by hot liquid produces little gas at all.",
         0.1,
         "How old was the yeast, and how warm was the liquid you mixed it with?"),
    ]),
]


def run(db: Session) -> str:
    added = 0
    for slug, description, domain, causes in SYMPTOMS:
        existing = db.scalar(select(Symptom).where(Symptom.slug == slug))
        if existing is not None:
            continue
        symptom = Symptom(slug=slug, description=description, domain=domain)
        db.add(symptom)
        db.flush()
        for cause, explanation, prior, follow_up in causes:
            db.add(
                SymptomCause(
                    symptom_id=symptom.id,
                    cause=cause,
                    explanation=explanation,
                    prior_weight=prior,
                    follow_up_question=follow_up,
                )
            )
        added += 1
    db.commit()
    return f"Added {added} symptoms ({len(SYMPTOMS)} in seed file)."


if __name__ == "__main__":
    with SessionLocal() as session:
        print(run(session))
