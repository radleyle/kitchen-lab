"""Public mechanism library: the science ideas behind techniques.

Think of mechanisms as the “why the pan behaves that way” chapter cards
(Maillard, gelatinization…). Techniques are the recipes that use them.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import ScientificMechanism, Technique
from app.schemas.lab import MechanismDetail, MechanismSummary, TechniqueSummary

router = APIRouter(prefix="/mechanisms", tags=["mechanisms"])


@router.get("", response_model=list[MechanismSummary])
def list_mechanisms(db: Session = Depends(get_db)) -> list[ScientificMechanism]:
    return list(
        db.scalars(select(ScientificMechanism).order_by(ScientificMechanism.name))
    )


@router.get("/{slug}", response_model=MechanismDetail)
def get_mechanism(slug: str, db: Session = Depends(get_db)) -> MechanismDetail:
    mechanism = db.scalar(
        select(ScientificMechanism).where(ScientificMechanism.slug == slug)
    )
    if mechanism is None:
        raise HTTPException(status_code=404, detail="Mechanism not found")

    techniques = list(
        db.scalars(
            select(Technique)
            .where(Technique.mechanism_id == mechanism.id)
            .order_by(Technique.name)
        )
    )
    return MechanismDetail(
        slug=mechanism.slug,
        name=mechanism.name,
        explanation=mechanism.explanation,
        techniques=[TechniqueSummary.model_validate(t) for t in techniques],
    )
