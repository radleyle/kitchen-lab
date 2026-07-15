"""Password hashing and JWT creation/verification."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


# ---------- Passwords ----------

def hash_password(password: str) -> str:
    # gensalt() generates a fresh random salt; it ends up embedded in the
    # hash string itself, so verification can re-use it later.
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------- JWTs ----------

def create_access_token(user_id: int) -> str:
    """Issue a signed token that says 'this is user N, valid until T'."""
    payload = {
        "sub": str(user_id),  # "subject" -- whom the token is about
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> int:
    """Verify the signature + expiry; return the user id inside.

    Raises jwt.InvalidTokenError (or subclasses like ExpiredSignatureError)
    if the token is forged, malformed, or expired.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    return int(payload["sub"])
