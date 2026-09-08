from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from api.schemas import (
    RegisterRequest,
    LoginRequest,
    AuthResponse
)

from api.auth.database import (
    create_user,
    get_user_by_email
)

from api.auth.security import (
    hash_password,
    verify_password,
    create_access_token
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=AuthResponse
)
def register(request: RegisterRequest):

    email = request.email.lower().strip()

    existing_user = get_user_by_email(email)

    if existing_user:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists."
        )


    password_hash = hash_password(
        request.password
    )


    user_id = create_user(
        full_name=request.full_name.strip(),
        email=email,
        password_hash=password_hash,
        created_at=datetime.now(
            timezone.utc
        ).isoformat()
    )


    token = create_access_token(
        user_id
    )


    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "full_name": request.full_name.strip(),
            "email": email
        }
    }


@router.post(
    "/login",
    response_model=AuthResponse
)
def login(request: LoginRequest):

    email = request.email.lower().strip()

    user = get_user_by_email(email)

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )


    password_valid = verify_password(
        request.password,
        user["password_hash"]
    )


    if not password_valid:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )


    token = create_access_token(
        user["id"]
    )


    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"]
        }
    }

