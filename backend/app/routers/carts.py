"""API quản lý giỏ hàng: /api/carts

Quy tắc nghiệp vụ (T3D25F6):
- Cùng món nhưng khác tuỳ chọn / ghi chú là dòng riêng; trùng hoàn toàn thì cộng dồn số lượng.
- Chặn món ăn đã hết hàng hoặc bị ẩn (và chặn tuỳ chọn hết/không hợp lệ).
- Chỉ được phép xem, thêm, sửa, xoá trên giỏ hàng của chính mình.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.schemas.cart import (
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartResponse,
)
from app.services import cart_service

router = APIRouter(prefix="/carts", tags=["Carts"])


@router.get("", response_model=CartResponse, summary="Xem giỏ hàng của mình")
@router.get("/me", response_model=CartResponse, summary="Xem giỏ hàng của mình")
def get_my_cart(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return cart_service.get_my_cart(db, current_user_id)


@router.post(
    "/items",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm món vào giỏ của mình (trùng hoàn toàn thì cộng dồn, khác tùy chọn/ghi chú tách dòng riêng)",
)
def add_item_to_my_cart(
    data: CartItemCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return cart_service.add_item_to_my_cart(db, current_user_id, data)


@router.put(
    "/items/{cart_item_id}",
    response_model=CartItemResponse,
    summary="Sửa món trong giỏ của mình (số lượng, tùy chọn, ghi chú)",
)
def update_my_cart_item(
    cart_item_id: int,
    data: CartItemUpdate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return cart_service.update_my_cart_item(db, current_user_id, cart_item_id, data)


@router.delete(
    "/items/{cart_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá 1 dòng món khỏi giỏ của mình",
)
def delete_my_cart_item(
    cart_item_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cart_service.remove_my_cart_item(db, current_user_id, cart_item_id)


@router.delete(
    "/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá toàn bộ món trong giỏ của mình",
)
@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá toàn bộ món trong giỏ của mình",
)
def clear_my_cart(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cart_service.clear_my_cart(db, current_user_id)


# Các route kèm {user_id} tương thích ngược nhưng vẫn bắt buộc đúng chủ sở hữu giỏ hàng
def _verify_target_user(target_user_id: int, current_user_id: int) -> None:
    if target_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chỉ được phép thao tác trên giỏ hàng của mình",
        )


@router.get(
    "/user/{target_user_id}",
    response_model=CartResponse,
    include_in_schema=False,
)
def get_user_cart(
    target_user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _verify_target_user(target_user_id, current_user_id)
    return cart_service.get_my_cart(db, current_user_id)


@router.post(
    "/user/{target_user_id}/items",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def add_item_to_user_cart(
    target_user_id: int,
    data: CartItemCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _verify_target_user(target_user_id, current_user_id)
    return cart_service.add_item_to_my_cart(db, current_user_id, data)


@router.delete(
    "/user/{target_user_id}/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
def clear_user_cart(
    target_user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _verify_target_user(target_user_id, current_user_id)
    cart_service.clear_my_cart(db, current_user_id)
