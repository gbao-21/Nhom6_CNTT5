"""Schemas cho bảng dishes và dish_options."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DishOptionBase(BaseModel):
    group_name: str = Field(default="Topping", min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(default=0, ge=0)
    is_available: bool = True
    is_required: bool = False
    allow_multiple: bool = False


class DishOptionCreate(DishOptionBase):
    pass


class DishOptionUpdate(BaseModel):
    group_name: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    price: Decimal | None = Field(default=None, ge=0)
    is_available: bool | None = None
    is_required: bool | None = None
    allow_multiple: bool | None = None


class DishOptionResponse(DishOptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dish_id: int
    created_at: datetime


class DishBase(BaseModel):
    category_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price: Decimal = Field(gt=0)
    image_url: str | None = Field(default=None, max_length=500)

    is_available: bool = True
    is_active: bool = True

    status: str = Field(default="AVAILABLE", max_length=30)
    is_featured: bool = False


class DishCreate(DishBase):
    options: list[DishOptionCreate] = Field(default_factory=list)


class DishUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    image_url: str | None = Field(default=None, max_length=500)

    is_available: bool | None = None
    is_active: bool | None = None

    status: str | None = Field(default=None, max_length=30)
    is_featured: bool | None = None


class DishResponse(DishBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    options: list[DishOptionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime