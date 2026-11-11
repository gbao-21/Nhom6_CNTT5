"""Model bảng delivery_areas (khu vực giao hàng & phí ship)."""
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, func

from app.db.base import Base


class DeliveryArea(Base):
    __tablename__ = "delivery_areas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False, unique=True)
    shipping_fee = Column(
        Numeric(15, 2),
        nullable=False,
        default=0,
        server_default="0",
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

