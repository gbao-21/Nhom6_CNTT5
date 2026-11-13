from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DiscountType(str, Enum):
    PERCENT = "PERCENT"
    FIXED = "FIXED"


class CouponStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# ── Admin tạo mã ────────────────────────────────────────────────────────────
class CouponCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50, description="Mã giảm giá")
    description: Optional[str] = Field(default=None, max_length=500)
    discount_type: DiscountType = DiscountType.FIXED
    discount_value: Decimal = Field(gt=0, description="Giá trị giảm (% hoặc số tiền)")
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0, description="Đơn tối thiểu")
    max_uses: Optional[int] = Field(default=None, gt=0, description="Giới hạn lượt dùng (None = vô hạn)")
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def validate_discount(self):
        if self.discount_type == DiscountType.PERCENT and self.discount_value > 100:
            raise ValueError("Giảm theo % không được vượt quá 100%")
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValueError("Thời gian kết thúc phải sau thời gian bắt đầu")
        return self


# ── Admin sửa mã ────────────────────────────────────────────────────────────
class CouponUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=500)
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = Field(default=None, gt=0)
    min_order_amount: Optional[Decimal] = Field(default=None, ge=0)
    max_uses: Optional[int] = Field(default=None, gt=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    status: Optional[CouponStatus] = None


# ── API kiểm tra mã từ Giỏ hàng ─────────────────────────────────────────────
class CouponApplyRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    order_amount: Decimal = Field(ge=0, description="Giá trị đơn hàng (subtotal) để kiểm tra đủ điều kiện")

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class CouponApplyResponse(BaseModel):
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    discount_amount: Decimal = Field(description="Số tiền được giảm thực tế")
    message: str


# ── Response ─────────────────────────────────────────────────────────────────
class CouponResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: Decimal
    min_order_amount: Decimal
    max_uses: Optional[int] = None
    used_count: int
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    status: CouponStatus
    created_at: datetime
    updated_at: datetime

