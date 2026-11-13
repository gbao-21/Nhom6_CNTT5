"""Model bảng vouchers (mã giảm giá).

Yêu cầu:
- mã (code)
- kiểu % hoặc số tiền (discount_type: PERCENT, FIXED)
- giá trị (discount_value)
- đơn tối thiểu (min_order_amount)
- giảm tối đa (max_discount_amount)
- hạn dùng (valid_from, valid_to / expired_at)
- số lượt (max_uses)
- đã dùng (used_count)
"""
from sqlalchemy import Column, DateTime, Integer, Numeric, String, func

from app.db.base import Base


class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Mã giảm giá (lưu chữ HOA, không phân biệt hoa thường khi tra cứu)
    code = Column(String(50), nullable=False, unique=True, index=True)

    description = Column(String(500), nullable=True)

    # PERCENT hoặc FIXED
    discount_type = Column(String(20), nullable=False, default="FIXED", server_default="FIXED")

    # Giá trị giảm: % (0-100) nếu PERCENT, số tiền nếu FIXED
    discount_value = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")

    # Giá trị đơn tối thiểu để áp dụng voucher (0 = không giới hạn)
    min_order_amount = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")

    # Số tiền giảm tối đa (đặc biệt hữu ích khi dùng loại PERCENT, NULL = không giới hạn)
    max_discount_amount = Column(Numeric(15, 2), nullable=True)

    # Hạn dùng
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    # Số lượt tối đa (NULL = không giới hạn)
    max_uses = Column(Integer, nullable=True)

    # Số lượt đã dùng
    used_count = Column(Integer, nullable=False, default=0, server_default="0")

    # ACTIVE hoặc INACTIVE
    status = Column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

