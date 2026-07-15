"""Users and their real-world kitchens.

Reading guide (applies to every model file):
- Mapped[str]        -> a required column of that Python type
- Mapped[str | None] -> a nullable column (row may leave it empty)
- mapped_column(...) -> extra SQL details: primary key, unique, foreign key
- relationship(...)  -> Python-side convenience: user.equipment gives the
                        related rows without writing a JOIN by hand
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # We store a HASH of the password, never the password itself.
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(100))
    # server_default=func.now() -> the DATABASE stamps the time on insert.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    kitchen_profile: Mapped["KitchenProfile | None"] = relationship(
        back_populates="user"
    )
    equipment: Mapped[list["Equipment"]] = relationship(back_populates="user")


class KitchenProfile(Base):
    """One per user: the facts about their kitchen that personalize answers."""

    __tablename__ = "kitchen_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True makes this one-to-one: a user can't have two profiles.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    # "My oven runs 15F cold" -> store -15 here, apply it to every oven temp.
    oven_offset_f: Mapped[int] = mapped_column(default=0)
    cooktop_type: Mapped[str | None] = mapped_column(String(30))  # gas/electric/induction
    elevation_m: Mapped[int | None] = mapped_column()  # water boils cooler up high
    measurement_system: Mapped[str] = mapped_column(String(10), default="us")  # us/metric

    # Flexible, variable-shaped data -> JSONB instead of dozens of columns.
    dietary_restrictions: Mapped[dict] = mapped_column(JSONB, default=dict)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)  # saltiness, doneness...

    user: Mapped[User] = relationship(back_populates="kitchen_profile")


class Equipment(Base):
    """A pan, oven, air fryer... anything that changes how we adjust recipes."""

    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50))  # e.g. "skillet", "oven", "air_fryer"
    name: Mapped[str] = mapped_column(String(120))  # e.g. "12-inch stainless skillet"
    details: Mapped[dict] = mapped_column(JSONB, default=dict)  # material, size, wattage

    user: Mapped[User] = relationship(back_populates="equipment")
