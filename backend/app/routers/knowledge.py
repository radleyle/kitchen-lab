"""Semantic search over the food-science knowledge base."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.rag.retrieval import search_passages

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search")
def search(
    q: str = Query(min_length=3, description="A cooking question or topic"),
    top_k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[dict]:
    """e.g. GET /knowledge/search?q=why did my sauce get thin after boiling"""
    return search_passages(db, q, top_k)
