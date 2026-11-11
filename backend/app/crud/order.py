"""CRUD cho bảng orders và order_items."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatusHistory
from app.schemas.order import OrderStatusUpdate


def get_orders(db: Session, user_id: int | None = None) -> list[Order]:
    query = select(Order).order_by(Order.id.desc())
    if user_id is not None:
        query = query.where(Order.user_id == user_id)
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


