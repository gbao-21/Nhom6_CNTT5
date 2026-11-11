from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class PaymentMethod(str, Enum):
    COD = "COD"
    BANK_TRANSFER = "BANK_TRANSFER"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    DELIVERING = "DELIVERING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Tùy chọn khách chọn khi đặt món
class OrderOptionCreate(BaseModel):
    option_id: int


class OrderItemCreate(BaseModel):
    dish_id: int
    selected_options: list[OrderOptionCreate] = Field(
        default_factory=list
    )
    note: str | None = None
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=100)
    recipient_phone: str = Field(min_length=1, max_length=20)
    delivery_address: str = Field(min_length=1, max_length=500)
    delivery_area_id: int
    payment_method: PaymentMethod
    desired_delivery_at: datetime | None = None
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# Tên và giá tùy chọn được lưu tại thời điểm đặt
class OrderOptionResponse(BaseModel):
    option_id: int
    name: str
    price: Decimal


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    dish_id: int | None = None
    dish_name: str
    dish_price: Decimal
    selected_options: list[OrderOptionResponse] | None = None
    options_price: Decimal
    note: str | None = None
    quantity: int
    line_total: Decimal
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_code: str
    user_id: int
    recipient_name: str
    recipient_phone: str
    delivery_address: str
    delivery_area_id: int
    shipping_fee: Decimal
    discount_amount: Decimal
    subtotal: Decimal
    total_amount: Decimal
    payment_method: PaymentMethod
    desired_delivery_at: datetime | None = None
    status: OrderStatus
    items: list[OrderItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime