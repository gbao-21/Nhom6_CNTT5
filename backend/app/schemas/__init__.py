"""Tập hợp toàn bộ Pydantic schemas của ứng dụng."""
from app.schemas.cart import (
    CartCreate,
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartOption,
    CartResponse,
)
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.schemas.chat_message import (
    ChatMessageCreate,
    ChatMessageMarkRead,
    ChatMessageResponse,
)
from app.schemas.delivery_area import (
    DeliveryAreaCreate,
    DeliveryAreaResponse,
    DeliveryAreaUpdate,
)
from app.schemas.dish import (
    DishCreate,
    DishOptionCreate,
    DishOptionResponse,
    DishResponse,
    DishUpdate,
)
from app.schemas.item import ItemCreate, ItemOut, ItemUpdate
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreate,
    OrderItemCreate,
    OrderItemResponse,
    OrderOptionCreate,
    OrderOptionResponse,
    OrderResponse,
    OrderStatus,
    OrderStatusHistoryResponse,
    OrderStatusUpdate,
    PaymentMethod,
)
from app.schemas.review import (
    ReviewCreate,
    ReviewReplyRequest,
    ReviewResponse,
    ReviewUpdate,
)
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.schemas.voucher import (
    VoucherCreate,
    VoucherDiscountType,
    VoucherResponse,
    VoucherStatus,
    VoucherUpdate,
)

__all__ = [
    "ItemCreate",
    "ItemOut",
    "ItemUpdate",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "CategoryCreate",
    "CategoryResponse",
    "CategoryUpdate",
    "DishCreate",
    "DishOptionCreate",
    "DishOptionResponse",
    "DishResponse",
    "DishUpdate",
    "DeliveryAreaCreate",
    "DeliveryAreaResponse",
    "DeliveryAreaUpdate",
    "CartCreate",
    "CartItemCreate",
    "CartItemResponse",
    "CartItemUpdate",
    "CartOption",
    "CartResponse",
    "OrderCancelRequest",
    "OrderCreate",
    "OrderItemCreate",
    "OrderItemResponse",
    "OrderOptionCreate",
    "OrderOptionResponse",
    "OrderResponse",
    "OrderStatus",
    "OrderStatusHistoryResponse",
    "OrderStatusUpdate",
    "PaymentMethod",
    "VoucherCreate",
    "VoucherUpdate",
    "VoucherResponse",
    "VoucherDiscountType",
    "VoucherStatus",
    "ReviewCreate",
    "ReviewUpdate",
    "ReviewReplyRequest",
    "ReviewResponse",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ChatMessageMarkRead",
]

