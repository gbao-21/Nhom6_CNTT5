"""CRUD cho bảng orders và order_items."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
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
) -> Order:
    order.status = data.status.value
    db.commit()
    db.refresh(order)
    return order

