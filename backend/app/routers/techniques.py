"""Public technique library: curated procedures with linked science."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.db import get_db
from app.models import Technique
from app.schemas.lab import TechniqueOut, TechniqueSummary

router = APIRouter(prefix="/techniques", tags=["techniques"])


@router.get("", response_model=list[TechniqueSummary])
def list_techniques(db: Session = Depends(get_db)) -> list[Technique]:
    return list(db.scalars(select(Technique).order_by(Technique.name)))


@router.get("/{slug}", response_model=TechniqueOut)
def get_technique(slug: str, db: Session = Depends(get_db)) -> Technique:
    technique = db.scalar(
        select(Technique)
        .where(Technique.slug == slug)
        .options(joinedload(Technique.mechanism))
    )
    if technique is None:
        raise HTTPException(status_code=404, detail="Technique not found")
    return technique
