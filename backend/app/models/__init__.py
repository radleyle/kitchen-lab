"""All database models.

Importing them here matters: Alembic discovers tables by looking at
Base.metadata, which only knows about classes that have been imported.
"""

from app.models.user import User, KitchenProfile, Equipment
from app.models.food import Ingredient, IngredientFunction, Substitution
from app.models.knowledge import (
    ScientificMechanism,
    Technique,
    KnowledgeSource,
    SourcePassage,
    SafetyRule,
)
from app.models.cooking import (
    Recipe,
    RecipeStep,
    Symptom,
    SymptomCause,
    AssistantConversation,
)
from app.models.experiment import (
    Experiment,
    ExperimentTrial,
    Observation,
    Attachment,
    NotebookEntry,
)

__all__ = [
    "User",
    "KitchenProfile",
    "Equipment",
    "Ingredient",
    "IngredientFunction",
    "Substitution",
    "ScientificMechanism",
    "Technique",
    "KnowledgeSource",
    "SourcePassage",
    "SafetyRule",
    "Recipe",
    "RecipeStep",
    "Symptom",
    "SymptomCause",
    "AssistantConversation",
    "Experiment",
    "ExperimentTrial",
    "Observation",
    "Attachment",
    "NotebookEntry",
]
