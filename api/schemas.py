from typing import Any

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
)


# ============================================================
# CHAT
# ============================================================

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )

    conversation_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )


class ChatResponse(BaseModel):
    type: str

    answer: str | None = None

    sources: list[str] = Field(
        default_factory=list
    )

    data: dict[str, Any] | None = None

    equipment: dict[str, Any] | None = None

    component: dict[str, Any] | None = None

    priority: str | None = None

    task: str | None = None

    reason: str | None = None

    required_parts: list[dict[str, Any]] = Field(
        default_factory=list
    )

    consumables: list[dict[str, Any]] = Field(
        default_factory=list
    )

    estimated_material_cost: float | None = None

    recommended_actions: list[Any] = Field(
        default_factory=list
    )

    safety: list[Any] = Field(
        default_factory=list
    )


# ============================================================
# AUTHENTICATION
# ============================================================

class RegisterRequest(BaseModel):

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):

    email: EmailStr

    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )


class AuthResponse(BaseModel):

    access_token: str

    token_type: str

    user: dict[str, Any]