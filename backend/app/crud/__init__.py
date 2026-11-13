"""Tập hợp các module CRUD thao tác trực tiếp với cơ sở dữ liệu."""
from app.crud import (
    cart,
    category,
    coupon,
    delivery_area,
    dish,
    item,
    order,
    review,
    user,
)

__all__ = [
    "item",
    "user",
    "category",
    "dish",
    "delivery_area",
    "cart",
    "order",
    "coupon",
    "review",
]

