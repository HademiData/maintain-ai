from typing import Any, Optional

from pydantic import BaseModel, Field,  EmailStr



class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: str


class ChatResponse(BaseModel):
    type: str
    answer: Optional[str] = None
    sources: list[str] = []
    data: Optional[dict[str, Any]] = None

    equipment: Optional[dict[str, Any]] = None
    component: Optional[dict[str, Any]] = None
    priority: Optional[str] = None
    task: Optional[str] = None
    reason: Optional[str] = None
    required_parts: list[dict[str, Any]] = []
    consumables: list[dict[str, Any]] = []
    estimated_material_cost: Optional[float] = None
    recommended_actions: list[Any] = []
    safety: list[Any] = []


# ==============================
# AUTHENTICATION
# ==============================

class RegisterRequest(BaseModel):

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    email: EmailStr

    password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )


class LoginRequest(BaseModel):

    email: EmailStr

    password: str


class AuthResponse(BaseModel):

    access_token: str

    token_type: str

    user: dict[str, Any]
