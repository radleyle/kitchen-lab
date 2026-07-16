"""HTTP endpoints exposing the deterministic calculators."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.calculators.baking import bakers_percentages, hydration_percent
from app.calculators.brine import salt_for_brine, salt_grams_to_tbsp
from app.calculators.scaling import scale_recipe
from app.calculators.units import volume_to_grams

router = APIRouter(prefix="/calculators", tags=["calculators"])


class BrineRequest(BaseModel):
    water_g: float = Field(gt=0, description="Water mass in grams (1 L = 1000 g)")
    brine_percent: float = Field(gt=0, le=26)
    salt_type: str = "table_salt"


@router.post("/brine")
def brine(body: BrineRequest) -> dict:
    try:
        grams = salt_for_brine(body.water_g, body.brine_percent)
        tbsp = salt_grams_to_tbsp(grams, body.salt_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"salt_g": grams, "salt_tbsp": tbsp, "salt_type": body.salt_type}


class ScaleRequest(BaseModel):
    ingredients: list[dict]  # [{"name", "amount", "unit"}]
    original_servings: int = Field(gt=0)
    target_servings: int = Field(gt=0)


@router.post("/scale")
def scale(body: ScaleRequest) -> list[dict]:
    try:
        scaled = scale_recipe(body.ingredients, body.original_servings, body.target_servings)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return [vars(s) for s in scaled]


class BakingRequest(BaseModel):
    ingredients_g: dict[str, float]  # {"bread flour": 500, "water": 375}


@router.post("/bakers-percentages")
def baking(body: BakingRequest) -> dict:
    try:
        return {
            "percentages": bakers_percentages(body.ingredients_g),
            "hydration_percent": hydration_percent(body.ingredients_g),
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


class VolumeToGramsRequest(BaseModel):
    amount: float = Field(gt=0)
    unit: str
    ingredient: str


@router.post("/volume-to-grams")
def vol_to_grams(body: VolumeToGramsRequest) -> dict:
    try:
        grams = volume_to_grams(body.amount, body.unit, body.ingredient)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"grams": round(grams, 1)}
