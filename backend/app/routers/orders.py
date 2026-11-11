"""API quản lý đơn hàng: /api/orders"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import order as order_crud
from app.db.session import get_db
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_order_or_404(order_id: int, db: Session = Depends(get_db)):
    order = order_crud.get_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy đơn hàng id={order_id}",
        )
    return order


@router.get("", response_model=list[OrderResponse])
def list_orders(user_id: int | None = None, db: Session = Depends(get_db)):
    return order_crud.get_orders(db, user_id=user_id)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order=Depends(get_order_or_404)):
    return order


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    user_id: int = 1,
    db: Session = Depends(get_db),
):
    return order_service.create_order_for_user(db, user_id=user_id, data=data)


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    data: OrderStatusUpdate,
    order=Depends(get_order_or_404),
    db: Session = Depends(get_db),
):
    return order_crud.update_order_status(db, order, data)

