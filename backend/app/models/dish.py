"""Model bảng dishes và dish_options."""
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

    # Trạng thái món ăn
    is_available = Column(Boolean, nullable=False, default=True, server_default="1")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    # AVAILABLE, OUT_OF_STOCK, HIDDEN
    status = Column(
        String(30),
        nullable=False,
        default="AVAILABLE",
        server_default="AVAILABLE",
    )

    # Đánh dấu món nổi bật
    is_featured = Column(Boolean, nullable=False, default=False, server_default="0")

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

    # Ví dụ: Size, Topping
    group_name = Column(
        String(100),
        nullable=False,
        default="Topping",
        server_default="Topping",
    )

    name = Column(String(100), nullable=False)
    price = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")

    is_available = Column(Boolean, nullable=False, default=True, server_default="1")
    is_required = Column(Boolean, nullable=False, default=False, server_default="0")
    allow_multiple = Column(Boolean, nullable=False, default=False, server_default="0")

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    dish = relationship("Dish", back_populates="options")