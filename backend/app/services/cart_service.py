"""Service xử lý nghiệp vụ giỏ hàng & tính tiền (Cart)."""
from sqlalchemy.orm import Session

from app.crud import cart as cart_crud
from app.models.cart import Cart, CartItem
from app.schemas.cart import CartCalculateRequest, CartItemCreate, CartItemUpdate


def get_my_cart(
    db: Session,
    current_user_id: int,
    delivery_area_id: int | None = None,
    voucher_code: str | None = None,
) -> Cart:
    return cart_crud.get_or_create_cart_by_user(
        db,
        user_id=current_user_id,
        delivery_area_id=delivery_area_id,
        voucher_code=voucher_code,
    )


def calculate_my_cart(
    db: Session,
    current_user_id: int,
    data: CartCalculateRequest,
) -> Cart:
    return cart_crud.get_or_create_cart_by_user(
        db,
        user_id=current_user_id,
        delivery_area_id=data.delivery_area_id,
        voucher_code=data.voucher_code,
    )


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
