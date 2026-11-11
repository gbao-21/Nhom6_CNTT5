from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CartOption(BaseModel):
    option_id: int


class CartItemCreate(BaseModel):
    dish_id: int
    selected_options: list[CartOption] = Field(default_factory=list)
    note: str | None = None
    quantity: int = Field(default=1, gt=0)


class CartItemUpdate(BaseModel):
    selected_options: list[CartOption] | None = None
    note: str | None = None
    quantity: int | None = Field(default=None, gt=0)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cart_id: int
    dish_id: int
    selected_options: list[CartOption] | None = None
    note: str | None = None
    quantity: int
    created_at: datetime
    updated_at: datetime


class CartCreate(BaseModel):
    user_id: int


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    items: list[CartItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
