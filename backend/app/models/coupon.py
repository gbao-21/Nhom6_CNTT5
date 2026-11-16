"""Model bảng coupons (mã giảm giá)."""
from sqlalchemy import Column, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Mã giảm giá – lưu chữ HOA, không phân biệt hoa thường khi tra cứu
    code = Column(String(50), nullable=False, unique=True, index=True)

    description = Column(String(500), nullable=True)

    # PERCENT hoặc FIXED
    discount_type = Column(String(20), nullable=False, default="FIXED", server_default="FIXED")

    # Giá trị giảm: % (0-100) nếu PERCENT, số tiền nếu FIXED
    discount_value = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")

    # Giá trị đơn hàng tối thiểu để áp dụng (0 = không yêu cầu)
    min_order_amount = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")

    # Số lượt dùng tối đa (NULL = không giới hạn)
    max_uses = Column(Integer, nullable=True)

    # Số lượt đã dùng
    used_count = Column(Integer, nullable=False, default=0, server_default="0")

    # Thời gian hiệu lực (NULL = không giới hạn)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    # ACTIVE, INACTIVE (admin ngừng thủ công)
    status = Column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

