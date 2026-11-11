"""Import mọi model ở đây để Base.metadata.create_all() "nhìn thấy" và tạo bảng.
Thêm model mới -> nhớ thêm 1 dòng import vào file này.
"""
from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish, DishOption
from app.models.item import Item
from app.models.order import Order, OrderItem, OrderStatusHistory
from app.models.user import User

__all__ = [
    "Item",
    "User",
    "Category",
    "Dish",
    "DishOption",
    "DeliveryArea",
    "Cart",
    "CartItem",
    "Order",
    "OrderItem",
    "OrderStatusHistory",
]
