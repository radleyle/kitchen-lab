"""Kitchen profile and equipment CRUD (auth required).

GET  /kitchen              full snapshot (profile + equipment)
PUT  /kitchen/profile      create or update the one profile per user
POST /kitchen/equipment    add a piece of equipment
PATCH /kitchen/equipment/{id}
DELETE /kitchen/equipment/{id}
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models import Equipment, KitchenProfile, User
from app.schemas.kitchen import (
    EquipmentCreate,
    EquipmentOut,
    EquipmentUpdate,
    KitchenProfileOut,
    KitchenProfileUpsert,
    KitchenSnapshotOut,
)

router = APIRouter(prefix="/kitchen", tags=["kitchen"])


@router.get("", response_model=KitchenSnapshotOut)
def get_kitchen(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> KitchenSnapshotOut:
    profile = db.scalar(
        select(KitchenProfile).where(KitchenProfile.user_id == user.id)
    )
    equipment = list(
        db.scalars(select(Equipment).where(Equipment.user_id == user.id))
    )
    return KitchenSnapshotOut(profile=profile, equipment=equipment)


@router.put("/profile", response_model=KitchenProfileOut)
def upsert_profile(
    body: KitchenProfileUpsert,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KitchenProfile:
    profile = db.scalar(
        select(KitchenProfile).where(KitchenProfile.user_id == user.id)
    )
    if profile is None:
        profile = KitchenProfile(user_id=user.id)
        db.add(profile)

    profile.oven_offset_f = body.oven_offset_f
    profile.cooktop_type = body.cooktop_type
    profile.elevation_m = body.elevation_m
    profile.measurement_system = body.measurement_system
    profile.dietary_restrictions = body.dietary_restrictions
    profile.preferences = body.preferences
    db.commit()
    db.refresh(profile)
    return profile


@router.post(
    "/equipment", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED
)
def add_equipment(
    body: EquipmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Equipment:
    item = Equipment(
        user_id=user.id,
        kind=body.kind,
        name=body.name,
        details=body.details,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/equipment/{equipment_id}", response_model=EquipmentOut)
def update_equipment(
    equipment_id: int,
    body: EquipmentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Equipment:
    item = db.get(Equipment, equipment_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Equipment not found")
    if body.kind is not None:
        item.kind = body.kind
    if body.name is not None:
        item.name = body.name
    if body.details is not None:
        item.details = body.details
    db.commit()
    db.refresh(item)
    return item


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(
    equipment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    item = db.get(Equipment, equipment_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Equipment not found")
    db.delete(item)
    db.commit()
