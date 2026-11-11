"""Model bảng dishes (món ăn) và dish_options (tùy chọn thêm của món)."""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")
    image_url = Column(String(500), nullable=True)

    # is_available: True = còn món, False = hết món
    is_available = Column(Boolean, nullable=False, default=True, server_default="1")
    # is_active: True = hiển thị trên menu, False = món bị ẩn
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    # status: AVAILABLE (còn bán), OUT_OF_STOCK (hết hàng), HIDDEN (ẩn)
    status = Column(
        String(30),
        nullable=False,
        default="AVAILABLE",
        server_default="AVAILABLE",
    )

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    category = relationship("Category", back_populates="dishes")
    options = relationship(
        "DishOption",
        back_populates="dish",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DishOption(Base):
    __tablename__ = "dish_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dish_id = Column(
        Integer,
        ForeignKey("dishes.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    price = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")
    is_available = Column(Boolean, nullable=False, default=True, server_default="1")

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    dish = relationship("Dish", back_populates="options")
