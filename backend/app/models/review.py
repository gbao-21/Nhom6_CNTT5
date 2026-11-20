"""Model bảng reviews (đánh giá món ăn, có thể gắn với đơn hàng)."""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Đơn hàng không bắt buộc khi đánh giá trực tiếp từ trang chi tiết món
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Món được đánh giá
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="SET NULL"), nullable=True)

    # Nội dung đánh giá
    rating = Column(SmallInteger, nullable=False)          # 1-5
    content = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)

    # Phản hồi của cửa hàng
    shop_reply = Column(Text, nullable=True)
    replied_at = Column(DateTime, nullable=True)

    # Admin ẩn đánh giá vi phạm
    is_hidden = Column(Boolean, nullable=False, default=False, server_default="0")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    order = relationship("Order")
    user = relationship("User")
    dish = relationship("Dish")

