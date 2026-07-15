"""KitchenLab backend entry point.

Run locally (inside Docker) with:
    docker compose up
Then open http://localhost:8000/docs to see the auto-generated API playground.
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.routers import auth

app = FastAPI(title=settings.app_name)

app.include_router(auth.router)

# CORS = browser security rule. By default a page served from localhost:3000
# (our frontend) is NOT allowed to call an API on localhost:8000 (a different
# "origin"). This middleware tells browsers: that's allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Is the kitchen open? (Does the backend process respond at all?)"""
    return {"status": "ok", "app": settings.app_name}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    """Can the kitchen reach the pantry? Runs a trivial query against Postgres.

    `Depends(get_db)` is FastAPI dependency injection: before calling this
    function, FastAPI runs get_db() and passes the resulting session in.
    """
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
