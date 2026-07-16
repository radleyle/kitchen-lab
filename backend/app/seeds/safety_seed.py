"""Seed USDA safe minimum internal temperatures into the database.

Run inside the container:
    docker compose exec backend python -m app.seeds.safety_seed

Idempotent: checks whether the source already exists and skips re-inserting.
Temperatures from the USDA Safe Minimum Internal Temperature Chart.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import KnowledgeSource, SafetyRule

USDA_SOURCE = {
    "title": "USDA Safe Minimum Internal Temperature Chart",
    "author": "USDA Food Safety and Inspection Service",
    "url": "https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/safe-temperature-chart",
    "source_type": "agency",
    "authority_level": "safety",
    "published_at": date(2020, 5, 11),
    "reviewed_at": date(2026, 7, 16),  # when we last verified the values
}

# (food label, temp F, temp C, rest minutes, matching keywords)
RULES = [
    ("Beef, pork, veal, lamb: steaks, chops, roasts", 145, 62.8, 3,
     ["beef", "steak", "pork chop", "pork loin", "pork roast", "veal", "lamb", "roast"]),
    ("Ground meats (beef, pork, veal, lamb)", 160, 71.1, 0,
     ["ground beef", "ground pork", "ground meat", "burger", "hamburger", "meatball", "meatloaf", "sausage"]),
    ("All poultry (whole, parts, ground)", 165, 73.9, 0,
     ["chicken", "turkey", "duck", "poultry", "ground chicken", "ground turkey", "wing", "thigh", "drumstick"]),
    ("Fish and shellfish", 145, 62.8, 0,
     ["fish", "salmon", "tuna", "cod", "tilapia", "halibut", "shrimp", "lobster", "crab", "scallop", "shellfish"]),
    ("Egg dishes", 160, 71.1, 0,
     ["egg", "quiche", "frittata", "custard"]),
    ("Ham, fresh or smoked (uncooked)", 145, 62.8, 3,
     ["ham", "fresh ham", "smoked ham"]),
    ("Leftovers and casseroles", 165, 73.9, 0,
     ["leftover", "casserole", "reheat"]),
]


def run(db: Session) -> str:
    existing = db.scalar(
        select(KnowledgeSource).where(KnowledgeSource.title == USDA_SOURCE["title"])
    )
    if existing is not None:
        return "Safety rules already seeded; nothing to do."

    source = KnowledgeSource(**USDA_SOURCE)
    db.add(source)
    db.flush()  # assigns source.id without committing yet

    for food, temp_f, temp_c, rest_min, keywords in RULES:
        db.add(
            SafetyRule(
                food=food,
                rule_type="internal_temp",
                min_internal_temp_c=temp_c,
                rest_time_min=rest_min,
                details={"temp_f": temp_f, "keywords": keywords},
                source_id=source.id,
            )
        )
    db.commit()
    return f"Seeded {len(RULES)} safety rules from: {source.title}"


if __name__ == "__main__":
    with SessionLocal() as session:
        print(run(session))
