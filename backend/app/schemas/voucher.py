from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VoucherDiscountType(str, Enum):
    PERCENT = "PERCENT"
    FIXED = "FIXED"


class VoucherStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# ── Tạo Voucher ─────────────────────────────────────────────────────────────
class VoucherCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50, description="Mã voucher")
    description: Optional[str] = Field(default=None, max_length=500)
    discount_type: VoucherDiscountType = VoucherDiscountType.FIXED
    discount_value: Decimal = Field(gt=0, description="Giá trị giảm (% hoặc số tiền)")
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0, description="Đơn tối thiểu")
    max_discount_amount: Optional[Decimal] = Field(
        default=None, ge=0, description="Số tiền giảm tối đa (khi áp dụng kiểu %)"
    )
    max_uses: Optional[int] = Field(default=None, gt=0, description="Số lượt tối đa (None = vô hạn)")
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def validate_discount_and_dates(self):
        if self.discount_type == VoucherDiscountType.PERCENT and self.discount_value > 100:
            raise ValueError("Giảm theo % không được vượt quá 100%")
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValueError("Hạn dùng kết thúc phải sau ngày bắt đầu")
        return self


# ── Cập nhật Voucher ────────────────────────────────────────────────────────
class VoucherUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=500)
    discount_type: Optional[VoucherDiscountType] = None
    discount_value: Optional[Decimal] = Field(default=None, gt=0)
    min_order_amount: Optional[Decimal] = Field(default=None, ge=0)
    max_discount_amount: Optional[Decimal] = Field(default=None, ge=0)
    max_uses: Optional[int] = Field(default=None, gt=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    status: Optional[VoucherStatus] = None


# ── Response Voucher ────────────────────────────────────────────────────────
class VoucherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    description: Optional[str] = None
    discount_type: VoucherDiscountType
    discount_value: Decimal
    min_order_amount: Decimal
    max_discount_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    used_count: int
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    status: VoucherStatus
    created_at: datetime
    updated_at: datetime

