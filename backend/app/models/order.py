from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_code = Column(
        String(30),
        nullable=False,
        unique=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    recipient_name = Column(String(100), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    delivery_address = Column(String(500), nullable=False)
    delivery_area_id = Column(
        Integer,
        ForeignKey("delivery_areas.id"),
        nullable=False,
    )

    shipping_fee = Column(
        Numeric(15, 2),
        nullable=False,
        default=0,
        server_default="0",
    )
    discount_amount = Column(
        Numeric(15, 2),
        nullable=False,
        default=0,
        server_default="0",
    )
    subtotal = Column(Numeric(15, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)

    # COD hoặc BANK_TRANSFER
    payment_method = Column(String(30), nullable=False)
    desired_delivery_at = Column(DateTime, nullable=True)

    # PENDING, CONFIRMED, PREPARING,
    # DELIVERING, COMPLETED, CANCELLED
    status = Column(
        String(30),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    items = relationship(
        "OrderItem",
        back_populates="order",
        passive_deletes="all",
    )
    status_history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at.asc()",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False,
    )
    dish_id = Column(
        Integer,
        ForeignKey("dishes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Tên và giá món tại thời điểm đặt
    dish_name = Column(String(255), nullable=False)
    dish_price = Column(Numeric(15, 2), nullable=False)

    # Tùy chọn gồm option_id, name, price tại thời điểm đặt
    selected_options = Column(JSON, nullable=True)
    options_price = Column(
        Numeric(15, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    note = Column(String(500), nullable=True)
    quantity = Column(Integer, nullable=False)
    line_total = Column(Numeric(15, 2), nullable=False)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    order = relationship("Order", back_populates="items")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    changed_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    note = Column(String(500), nullable=True)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    order = relationship("Order", back_populates="status_history")
    user = relationship("User", foreign_keys=[changed_by])
