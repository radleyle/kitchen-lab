"""Load a user's kitchen snapshot for personalization."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Equipment, KitchenProfile, User


def load_kitchen_snapshot(db: Session, user: User | None) -> dict | None:
    """Return a JSON-ready snapshot, or None when there's no logged-in user."""
    if user is None:
        return None

    profile = db.scalar(
        select(KitchenProfile).where(KitchenProfile.user_id == user.id)
    )
    equipment = list(
        db.scalars(select(Equipment).where(Equipment.user_id == user.id))
    )

    if profile is None and not equipment:
        return None

    return {
        "profile": (
            {
                "oven_offset_f": profile.oven_offset_f,
                "cooktop_type": profile.cooktop_type,
                "elevation_m": profile.elevation_m,
                "measurement_system": profile.measurement_system,
                "dietary_restrictions": profile.dietary_restrictions or {},
                "preferences": profile.preferences or {},
            }
            if profile
            else {}
        ),
        "equipment": [
            {
                "id": e.id,
                "kind": e.kind,
                "name": e.name,
                "details": e.details or {},
            }
            for e in equipment
        ],
    }
