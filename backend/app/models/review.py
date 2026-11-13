"""Model bảng reviews (đánh giá món ăn & đơn hàng).

Yêu cầu:
- đơn (order_id)
- món (dish_id)
- người đánh giá (user_id)
- số sao (rating)
- nội dung (content)
- ảnh (image_url)
- trả lời của cửa hàng (shop_reply, replied_at)
"""
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Đơn hàng được đánh giá
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Món ăn được đánh giá (nullable nếu đánh giá tổng thể đơn hàng)
    dish_id = Column(
        Integer,
        ForeignKey("dishes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Khách hàng thực hiện đánh giá
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Số sao (1 đến 5 sao)
    rating = Column(Integer, nullable=False, default=5)

    # Nội dung đánh giá
    content = Column(Text, nullable=True)

    # Hình ảnh đính kèm (URL ảnh món thực tế nhận được)
    image_url = Column(String(500), nullable=True)

    # Trả lời của cửa hàng
    shop_reply = Column(Text, nullable=True)
    replied_at = Column(DateTime, nullable=True)

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

    # Quan hệ liên kết
    order = relationship("Order", backref="reviews")
    dish = relationship("Dish", backref="reviews")
    user = relationship("User", backref="reviews")

