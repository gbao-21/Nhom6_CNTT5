from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CartOption(BaseModel):
    option_id: int
    name: str | None = None
    price: float = 0


class CartItemCreate(BaseModel):
    dish_id: int
    selected_options: list[CartOption] = Field(default_factory=list)
    note: str | None = None
    quantity: int = Field(default=1, gt=0)


class CartItemUpdate(BaseModel):
    selected_options: list[CartOption] | None = None
    note: str | None = None
    quantity: int | None = Field(default=None, gt=0)


class CartCalculateRequest(BaseModel):
    delivery_area_id: int | None = Field(
        default=None,
        description="ID khu vực giao hàng để tính phí ship",
    )
    voucher_code: str | None = Field(
        default=None,
        description="Mã khuyến mãi / giảm giá (ví dụ: GIAM10, GIAM20K, FREESHIP)",
    )


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cart_id: int
    dish_id: int
    dish_name: str | None = None
    dish_image_url: str | None = None

    # Giá món lúc thêm vào giỏ và giá món hiện tại trên server
    old_price: float | None = None
    dish_price: float = 0
    options_price: float = 0
    unit_price: float = 0

    selected_options: list[CartOption] | None = None
    note: str | None = None
    quantity: int
    line_total: float = 0

    # Trạng thái kiểm tra món hết / ẩn hoặc đổi giá
    is_available: bool = True
    is_price_changed: bool = False
    warnings: list[str] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime


class CartCreate(BaseModel):
    user_id: int


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    items: list[CartItemResponse] = Field(default_factory=list)

    # Tổng hợp số lượng & tính tiền ở server
    total_items: int = 0
    total_quantity: int = 0
    subtotal: float = 0
    delivery_area_id: int | None = None
    shipping_fee: float = 0
    voucher_code: str | None = None
    discount_amount: float = 0
    total_amount: float = 0

    # Cờ & thông báo cảnh báo khi có món đã hết hoặc đổi giá
    has_unavailable_items: bool = False
    has_price_changes: bool = False
    can_checkout: bool = True
    warnings: list[str] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
