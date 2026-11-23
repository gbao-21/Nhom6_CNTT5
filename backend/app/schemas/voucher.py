"""Pydantic schemas cho Voucher."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class VoucherBase(BaseModel):
    code: str = Field(..., max_length=50)
    discount_type: str = Field(default="PERCENT", description="PERCENT hoặc FIXED")
    discount_value: Decimal = Field(..., ge=0)
    min_order_amount: Decimal = Field(default=Decimal(0), ge=0)
    max_discount_amount: Optional[Decimal] = Field(default=None, ge=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    max_uses: Optional[int] = Field(default=None, gt=0)


class VoucherCreate(VoucherBase):
    pass


class VoucherUpdate(BaseModel):
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    min_order_amount: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    max_uses: Optional[int] = None
    status: Optional[str] = None


class VoucherResponse(VoucherBase):
    id: int
    used_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

