"""Database plumbing (SQLAlchemy).

Mental model:
- engine  = the phone line to Postgres (created once, at startup)
- session = one phone call (opened per request, closed after)
- Base    = the parent class all our table-models will inherit from
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)

# A factory that makes sessions bound to our engine.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """All table models (User, Recipe, ...) will inherit from this."""


def get_db():
    """FastAPI 'dependency': opens a session for one request, then closes it.

    The yield hands the session to the endpoint function; the finally block
    guarantees we hang up the phone even if the endpoint raised an error.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
