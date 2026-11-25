"""API quản lý đơn hàng (Khách hàng & Nhân viên xử lý đơn): /api/orders"""
from datetime import date
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.order_status import ORDER_STATUS_LABELS
from app.crud import order as order_crud
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreate,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
)
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])

NEXT_STEP_MAP: dict[str, str] = {
    "PENDING": "CONFIRMED",
    "CONFIRMED": "PREPARING",
    "PREPARING": "DELIVERING",
    "DELIVERING": "COMPLETED",
}


def get_order_or_404(order_id: int, db: Session = Depends(get_db)):
    order = order_crud.get_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy đơn hàng id={order_id}",
        )
    return order


@router.get(
    "",
    response_model=list[OrderResponse],
    summary="Danh sách đơn hàng (hỗ trợ lọc theo trạng thái, ngày, tìm theo mã đơn/SĐT)",
)
@router.get(
    "/staff",
    response_model=list[OrderResponse],
    summary="[Nhân viên] Danh sách đơn mới/đang làm theo thời gian, lọc theo ngày/trạng thái, tìm theo mã/SĐT",
)
def list_orders(
    user_id: int | None = Query(default=None, description="Lọc theo ID khách hàng"),
    status: OrderStatus | None = Query(default=None, description="Lọc theo trạng thái đơn"),
    active_only: bool = Query(
        default=False,
        description="True = chỉ lấy đơn mới / đang làm (PENDING, CONFIRMED, PREPARING, DELIVERING)",
    ),
    q: str | None = Query(
        default=None,
        description="Tìm kiếm theo mã đơn (order_code) hoặc số điện thoại khách (recipient_phone)",
    ),
    order_date: date | None = Query(
        default=None,
        alias="date",
        description="Lọc theo ngày đặt đơn (YYYY-MM-DD)",
    ),
    start_date: date | None = Query(default=None, description="Từ ngày (YYYY-MM-DD)"),
    end_date: date | None = Query(default=None, description="Đến ngày (YYYY-MM-DD)"),
    sort: str = Query(
        default="desc",
        description="Sắp xếp theo thời gian: 'asc' (đơn cũ làm trước) hoặc 'desc' (đơn mới nhất lên đầu)",
    ),
    db: Session = Depends(get_db),
):
    return order_crud.get_orders(
        db=db,
        user_id=user_id,
        status=status.value if status else None,
        active_only=active_only,
        q=q,
        order_date=order_date,
        start_date=start_date,
        end_date=end_date,
        sort=sort,
    )


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


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="API đặt món trong transaction (kiểm tra món còn bán, lưu giá & tùy chọn lúc đặt, tạo đơn + chi tiết, xoá giỏ)",
)
@router.post(
    "/checkout",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="API đặt món từ giỏ hàng trong transaction",
)
def create_order(
    data: OrderCreate,
    current_user_id: int = Depends(get_current_user_id),
    x_idempotency_key: str | None = Header(
        default=None,
        alias="X-Idempotency-Key",
        description="Khóa chống bấm đặt 2 lần (tùy chọn)",
    ),
    db: Session = Depends(get_db),
):
    return order_service.create_order_for_user(
        db=db,
        user_id=current_user_id,
        data=data,
        idempotency_key=x_idempotency_key,
    )


@router.post(
    "/{order_id}/confirm",
    response_model=OrderResponse,
    summary="[Nhân viên] Xác nhận đơn hàng mới (PENDING -> CONFIRMED) và ghi lịch sử",
)
def confirm_order(
    note: str | None = Query(default="Nhân viên xác nhận đơn hàng"),
    changed_by: int | None = Query(default=None),
    order=Depends(get_order_or_404),
    db: Session = Depends(get_db),
):
    return order_service.change_order_status(
        db=db,
        order=order,
        new_status="CONFIRMED",
        changed_by=changed_by,
        note=note or "Nhân viên xác nhận đơn hàng",
    )


@router.post(
    "/{order_id}/next-status",
    response_model=OrderResponse,
    summary="[Nhân viên] Chuyển nhanh đơn sang bước tiếp theo đúng luồng (PENDING -> CONFIRMED -> PREPARING -> DELIVERING -> COMPLETED)",
)
def advance_order_next_status(
    note: str | None = Query(default=None, description="Ghi chú khi chuyển trạng thái"),
    changed_by: int | None = Query(default=None),
    order=Depends(get_order_or_404),
    db: Session = Depends(get_db),
):
    next_status = NEXT_STEP_MAP.get(order.status)
    if not next_status:
        raise HTTPException(
            status_code=400,
            detail=f"Đơn hàng đang ở trạng thái '{order.status}' ({ORDER_STATUS_LABELS.get(order.status, order.status)}), không thể chuyển sang bước tiếp theo",
        )
    label = ORDER_STATUS_LABELS.get(next_status, next_status)
    return order_service.change_order_status(
        db=db,
        order=order,
        new_status=next_status,
        changed_by=changed_by,
        note=note or f"Nhân viên chuyển trạng thái sang {label}",
    )


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


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="[Nhân viên] Chuyển trạng thái đơn hàng đúng luồng (chặn chuyển sai luồng) và ghi lịch sử",
)
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
