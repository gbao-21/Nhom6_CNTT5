"""API quản lý đơn hàng: /api/orders"""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import order as order_crud
from app.db.session import get_db
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreate,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
)
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


@router.get("/my-orders", response_model=list[OrderResponse])
def get_my_orders(
    status: OrderStatus | None = None,
    user_id: int | None = None,
    x_user_id: int | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    """API Đơn của tôi: Khách xem danh sách đơn theo trạng thái, chỉ xem đơn của mình."""
    effective_user_id = user_id or x_user_id or 1
    return order_crud.get_user_orders(
        db,
        user_id=effective_user_id,
        status=status.value if status else None,
    )


@router.get("/my-orders/{order_id}", response_model=OrderResponse)
def get_my_order_detail(
    order_id: int,
    user_id: int | None = None,
    x_user_id: int | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    """API Theo dõi đơn: xem chi tiết đơn kèm món, tuỳ chọn và dòng thời gian trạng thái (chỉ xem đơn của mình)."""
    effective_user_id = user_id or x_user_id or 1
    order = order_crud.get_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy đơn hàng id={order_id}",
        )
    if order.user_id != effective_user_id:
        raise HTTPException(
            status_code=403,
            detail="Bạn chỉ có quyền xem đơn hàng của chính mình",
        )
    return order


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


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    data: OrderCancelRequest,
    user_id: int | None = None,
    x_user_id: int | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    """API huỷ đơn theo điều kiện:
    - Khách huỷ khi còn Chờ xác nhận (PENDING).
    - Nhân viên huỷ trước Đang giao kèm lý do (VD: hết món).
    - Ghi lịch sử trạng thái OrderStatusHistory.
    """
    effective_user_id = data.user_id or user_id or x_user_id
    return order_service.cancel_order(
        db=db,
        order_id=order_id,
        user_id=effective_user_id,
        reason=data.reason,
        role=data.role,
    )


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    data: OrderStatusUpdate,
    order=Depends(get_order_or_404),
    db: Session = Depends(get_db),
):
    return order_service.change_order_status(
        db=db,
        order=order,
        new_status=data.status.value,
        changed_by=data.changed_by,
        note=data.note,
    )

