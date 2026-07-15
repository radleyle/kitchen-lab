"""Pydantic schemas: the shapes of data crossing the API boundary.

Models (SQLAlchemy) describe database tables; schemas (Pydantic) describe
JSON going in and out of HTTP. Keeping them separate means we control
exactly what leaves the building -- e.g. UserOut has no hashed_password,
so it's impossible to leak it in a response.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr  # validates it actually looks like an email
    password: str = Field(min_length=8)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    # from_attributes lets Pydantic read fields straight off a SQLAlchemy
    # User object, so endpoints can just `return user`.
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str | None
