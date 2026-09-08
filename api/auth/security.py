import os

from datetime import datetime, timedelta, timezone

from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError



from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from api.auth.database import get_user_by_id



# ==========================================
# PASSWORD HASHING
# ==========================================

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    try:

        return password_hasher.verify(
            hashed_password,
            plain_password
        )

    except VerifyMismatchError:

        return False


# ==========================================
# JWT
# ==========================================

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-secret-key"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def create_access_token(user_id: int):

    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token."
            )

    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    user = get_user_by_id(int(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists."
        )

    return user