"""Service xử lý nghiệp vụ giỏ hàng (Cart)."""
from sqlalchemy.orm import Session

from app.crud import cart as cart_crud
from app.models.cart import Cart, CartItem
from app.schemas.cart import CartItemCreate, CartItemUpdate


def get_my_cart(db: Session, current_user_id: int) -> Cart:
    return cart_crud.get_or_create_cart_by_user(db, current_user_id)


def add_item_to_my_cart(
    db: Session,
    current_user_id: int,
    data: CartItemCreate,
) -> CartItem:
    return cart_crud.add_item_to_user_cart(db, current_user_id, data)


def update_my_cart_item(
    db: Session,
    current_user_id: int,
    cart_item_id: int,
    data: CartItemUpdate,
) -> CartItem:
    return cart_crud.update_user_cart_item(db, current_user_id, cart_item_id, data)


def remove_my_cart_item(
    db: Session,
    current_user_id: int,
    cart_item_id: int,
) -> None:
    cart_crud.delete_user_cart_item(db, current_user_id, cart_item_id)


def clear_my_cart(db: Session, current_user_id: int) -> None:
    cart_crud.clear_user_cart(db, current_user_id)

