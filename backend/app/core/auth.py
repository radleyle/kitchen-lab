"""The get_current_user dependency: the bouncer checking wristbands.

Any endpoint that declares `user: User = Depends(get_current_user)` is
automatically protected -- FastAPI runs this first, and if the token is
missing/forged/expired the endpoint never even executes.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import User

# Extracts the "Authorization: Bearer <token>" header for us,
# and makes the /docs page show an Authorize button.
bearer_scheme = HTTPBearer()
# Same header, but missing token is OK -- used by endpoints that personalize
# when logged in and still work anonymously.
optional_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the user when a valid token is present; otherwise None."""
    if credentials is None:
        return None
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        return None
    return db.get(User, user_id)
