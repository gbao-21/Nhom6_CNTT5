"""Schemas cho bảng users."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    role: str = Field(default="CUSTOMER", max_length=30)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=100)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    role: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

