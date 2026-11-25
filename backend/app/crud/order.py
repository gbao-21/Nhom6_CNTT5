"""CRUD cho bảng orders và order_items."""
from datetime import date, datetime, time
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatusHistory
from app.schemas.order import OrderStatusUpdate


def get_orders(
    db: Session,
    user_id: int | None = None,
    status: str | None = None,
    active_only: bool = False,
    q: str | None = None,
    order_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort: str = "desc",
) -> list[Order]:
    """Lấy danh sách đơn hàng hỗ trợ lọc cho nhân viên:
    - user_id: lọc theo khách hàng
    - status: lọc theo trạng thái cụ thể (PENDING, CONFIRMED, PREPARING, DELIVERING, COMPLETED, CANCELLED)
    - active_only: True -> chỉ lấy đơn mới / đang làm (PENDING, CONFIRMED, PREPARING, DELIVERING)
    - q: tìm kiếm theo mã đơn (order_code), SĐT người nhận (recipient_phone), hoặc tên người nhận
    - order_date / start_date / end_date: lọc theo ngày tạo đơn
    - sort: 'asc' (đơn cũ lên trước theo thời gian) hoặc 'desc' (đơn mới nhất lên trước)
    """
    query = select(Order)

    if user_id is not None:
        query = query.where(Order.user_id == user_id)

    if status is not None and status.strip():
        query = query.where(Order.status == status.strip().upper())
    elif active_only:
        query = query.where(
            Order.status.in_(["PENDING", "CONFIRMED", "PREPARING", "DELIVERING"])
        )

    if q is not None and q.strip():
        keyword = f"%{q.strip()}%"
        query = query.where(
            or_(
                Order.order_code.ilike(keyword),
                Order.recipient_phone.ilike(keyword),
                Order.recipient_name.ilike(keyword),
            )
        )

    if order_date is not None:
        day_start = datetime.combine(order_date, time.min)
        day_end = datetime.combine(order_date, time.max)
        query = query.where(Order.created_at >= day_start, Order.created_at <= day_end)
    else:
        if start_date is not None:
            query = query.where(
                Order.created_at >= datetime.combine(start_date, time.min)
            )
        if end_date is not None:
            query = query.where(
                Order.created_at <= datetime.combine(end_date, time.max)
            )

    if sort.lower() == "asc":
        query = query.order_by(Order.created_at.asc(), Order.id.asc())
    else:
        query = query.order_by(Order.created_at.desc(), Order.id.desc())

    return list(db.scalars(query))


def get_order(db: Session, order_id: int) -> Order | None:
    return db.get(Order, order_id)


def get_order_by_code(db: Session, order_code: str) -> Order | None:
    return db.scalar(select(Order).where(Order.order_code == order_code))


def update_order_status(
    db: Session,
    order: Order,
    data: OrderStatusUpdate,
    changed_by: int | None = None,
) -> Order:
    old_status = order.status
    order.status = data.status.value
    history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=data.status.value,
        changed_by=data.changed_by or changed_by,
        note=data.note or f"Chuyển trạng thái sang {data.status.value}",
    )
    db.add(history)
    db.commit()
    db.refresh(order)
    return order


def get_user_orders(
    db: Session,
    user_id: int,
    status: str | None = None,
) -> list[Order]:
    query = select(Order).where(Order.user_id == user_id)
    if status is not None:
        query = query.where(Order.status == status)
    query = query.order_by(Order.id.desc())
    return list(db.scalars(query))


def add_order_status_history(
    db: Session,
    order_id: int,
    old_status: str | None,
    new_status: str,
    changed_by: int | None = None,
    note: str | None = None,
) -> OrderStatusHistory:
    history = OrderStatusHistory(
        order_id=order_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        note=note,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history
