"""Schemas cho bảng delivery_areas."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class DeliveryAreaBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    shipping_fee: Decimal = Field(default=0, ge=0)
    is_active: bool = True


class DeliveryAreaCreate(DeliveryAreaBase):
    pass


class DeliveryAreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    shipping_fee: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class DeliveryAreaResponse(DeliveryAreaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

