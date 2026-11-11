"""Tập hợp các router API của ứng dụng."""
from app.routers import (
    carts,
    categories,
    delivery_areas,
    dishes,
    health,
    items,
    orders,
    users,
)

__all__ = [
    "health",
    "items",
    "users",
    "categories",
    "dishes",
    "delivery_areas",
    "carts",
    "orders",
]

