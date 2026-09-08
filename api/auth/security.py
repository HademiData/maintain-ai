import os

from datetime import datetime, timedelta, timezone

from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


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