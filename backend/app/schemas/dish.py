"""Schemas cho bảng dishes và dish_options."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class DishOptionBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(default=0, ge=0)
    is_available: bool = True


class DishOptionCreate(DishOptionBase):
    pass


class DishOptionResponse(DishOptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dish_id: int
    created_at: datetime


class DishBase(BaseModel):
    category_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price: Decimal = Field(default=0, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    is_available: bool = True


class DishCreate(DishBase):
    options: list[DishOptionCreate] = Field(default_factory=list)


class DishUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    is_available: bool | None = None


class DishResponse(DishBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    options: list[DishOptionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

