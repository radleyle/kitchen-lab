"""Request/response shapes for kitchen profile and equipment."""

from pydantic import BaseModel, ConfigDict, Field


class KitchenProfileUpsert(BaseModel):
    oven_offset_f: int = Field(default=0, ge=-50, le=50)
    cooktop_type: str | None = Field(default=None, max_length=30)
    elevation_m: int | None = Field(default=None, ge=0, le=6000)
    measurement_system: str = Field(default="us", pattern="^(us|metric)$")
    dietary_restrictions: dict = Field(default_factory=dict)
    preferences: dict = Field(default_factory=dict)


class KitchenProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    oven_offset_f: int
    cooktop_type: str | None
    elevation_m: int | None
    measurement_system: str
    dietary_restrictions: dict
    preferences: dict


class EquipmentCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=120)
    details: dict = Field(default_factory=dict)


class EquipmentUpdate(BaseModel):
    kind: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    details: dict | None = None


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    name: str
    details: dict


class KitchenSnapshotOut(BaseModel):
    profile: KitchenProfileOut | None
    equipment: list[EquipmentOut]
