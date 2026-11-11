"""CRUD cho bảng carts và cart_items."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.schemas.cart import CartItemCreate, CartItemUpdate


def get_or_create_cart_by_user(db: Session, user_id: int) -> Cart:
    cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def add_item_to_cart(db: Session, cart: Cart, data: CartItemCreate) -> CartItem:
    item = CartItem(
        cart_id=cart.id,
        dish_id=data.dish_id,
        selected_options=[opt.model_dump() for opt in data.selected_options],
        note=data.note,
        quantity=data.quantity,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_cart_item(db: Session, cart_item_id: int) -> CartItem | None:
    return db.get(CartItem, cart_item_id)


def update_cart_item(
    db: Session,
    cart_item: CartItem,
    data: CartItemUpdate,
) -> CartItem:
    payload = data.model_dump(exclude_unset=True)
    if "selected_options" in payload and payload["selected_options"] is not None:
        payload["selected_options"] = [opt.model_dump() for opt in data.selected_options]
    for field, value in payload.items():
        setattr(cart_item, field, value)
    db.commit()
    db.refresh(cart_item)
    return cart_item


def delete_cart_item(db: Session, cart_item: CartItem) -> None:
    db.delete(cart_item)
    db.commit()


def clear_cart(db: Session, cart: Cart) -> None:
    for item in list(cart.items):
        db.delete(item)
    db.commit()

