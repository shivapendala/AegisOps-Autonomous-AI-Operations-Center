"""Pydantic schemas for Users."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "OPERATOR"
    is_active: bool = True


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
