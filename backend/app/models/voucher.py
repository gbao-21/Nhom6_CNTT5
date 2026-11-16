"""Model bảng vouchers (phiếu giảm giá có thể gán cho người dùng cụ thể).

Khác Coupon (mã công khai dùng chung):
  Voucher được tạo cá nhân hoá, gắn với user, có giảm tối đa.
"""
from sqlalchemy import Column, DateTime, Integer, Numeric, String, func

from app.db.base import Base


class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Mã voucher (unique)
    code = Column(String(50), nullable=False, unique=True, index=True)

    # PERCENT hoặc FIXED
    discount_type = Column(String(20), nullable=False, default="PERCENT", server_default="PERCENT")

    # Giá trị giảm: % (0-100) hoặc số tiền cố định
    discount_value = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")

    # Đơn hàng tối thiểu để áp dụng (0 = không yêu cầu)
    min_order_amount = Column(Numeric(15, 2), nullable=False, default=0, server_default="0")

    # Giảm tối đa (NULL = không giới hạn, áp dụng cho loại PERCENT)
    max_discount_amount = Column(Numeric(15, 2), nullable=True)

    # Thời hạn sử dụng
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)

    # Số lượt dùng tối đa và số lượt đã dùng
    max_uses = Column(Integer, nullable=True)
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

