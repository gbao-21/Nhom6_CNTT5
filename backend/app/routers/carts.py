"""API quản lý giỏ hàng: /api/carts"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import cart as cart_crud
from app.db.session import get_db
from app.schemas.cart import (
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartResponse,
)

router = APIRouter(prefix="/carts", tags=["Carts"])


@router.get("/user/{user_id}", response_model=CartResponse)
def get_user_cart(user_id: int, db: Session = Depends(get_db)):
    return cart_crud.get_or_create_cart_by_user(db, user_id)


@router.post(
    "/user/{user_id}/items",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_item_to_user_cart(
    user_id: int,
    data: CartItemCreate,
    db: Session = Depends(get_db),
):
    cart = cart_crud.get_or_create_cart_by_user(db, user_id)
    return cart_crud.add_item_to_cart(db, cart, data)


@router.put("/items/{cart_item_id}", response_model=CartItemResponse)
def update_cart_item(
    cart_item_id: int,
    data: CartItemUpdate,
    db: Session = Depends(get_db),
):
    cart_item = cart_crud.get_cart_item(db, cart_item_id)
    if cart_item is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy món trong giỏ id={cart_item_id}",
        )
    return cart_crud.update_cart_item(db, cart_item, data)


@router.delete("/items/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart_item(cart_item_id: int, db: Session = Depends(get_db)):
    cart_item = cart_crud.get_cart_item(db, cart_item_id)
    if cart_item is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy món trong giỏ id={cart_item_id}",
        )
    cart_crud.delete_cart_item(db, cart_item)


@router.delete("/user/{user_id}/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_user_cart(user_id: int, db: Session = Depends(get_db)):
    cart = cart_crud.get_or_create_cart_by_user(db, user_id)
    cart_crud.clear_cart(db, cart)

