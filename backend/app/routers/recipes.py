"""Cook + Adapt endpoints.

POST /recipes/generate  natural-language request -> annotated recipe
POST /recipes/adapt     pasted recipe text -> standardized, annotated recipe
GET  /recipes/{id}      read back a persisted recipe with its steps

Optional Bearer token personalizes from the kitchen profile (oven offset,
equipment, dietary restrictions) and owns the saved recipe.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_optional_user
from app.core.db import get_db
from app.kitchen.context import load_kitchen_snapshot
from app.models import Recipe, User
from app.recipes.generator import adapt_recipe, generate_recipe

router = APIRouter(prefix="/recipes", tags=["recipes"])


class GenerateRequest(BaseModel):
    request: str = Field(min_length=5, max_length=1000)
    servings: int | None = Field(default=None, ge=1, le=50)


class AdaptRequest(BaseModel):
    recipe_text: str = Field(min_length=20, max_length=15000)
    source_url: str | None = Field(default=None, max_length=500)


@router.get("")
def list_my_recipes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Cookbook shelf: recipes generated while this user was signed in."""
    rows = list(
        db.scalars(
            select(Recipe)
            .where(Recipe.user_id == user.id)
            .order_by(Recipe.id.desc())
        )
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "servings": r.servings,
        }
        for r in rows
    ]


@router.post("/generate")
def generate(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    snapshot = load_kitchen_snapshot(db, user)
    return generate_recipe(
        db,
        body.request,
        body.servings,
        kitchen_snapshot=snapshot,
        user_id=user.id if user else None,
    )


@router.post("/adapt")
def adapt(
    body: AdaptRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    snapshot = load_kitchen_snapshot(db, user)
    return adapt_recipe(
        db,
        body.recipe_text,
        body.source_url,
        kitchen_snapshot=snapshot,
        user_id=user.id if user else None,
    )


@router.get("/{recipe_id}")
def get_recipe(recipe_id: int, db: Session = Depends(get_db)) -> dict:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {
        "id": recipe.id,
        "title": recipe.title,
        "description": recipe.description,
        "servings": recipe.servings,
        "source_url": recipe.source_url,
        "ingredients": recipe.ingredients,
        "steps": [
            {
                "position": s.position,
                "instruction": s.instruction,
                "why": s.why,
                "science": s.science,
                "critical_temp_c": s.critical_temp_c,
                "visual_cues": s.visual_cues,
            }
            for s in recipe.steps
        ],
    }
