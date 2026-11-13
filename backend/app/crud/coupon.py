"""CRUD thao tác với bảng coupons."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.coupon import Coupon
from app.schemas.coupon import CouponCreate, CouponUpdate


# ── Lấy danh sách ────────────────────────────────────────────────────────────
def get_coupons(db: Session, skip: int = 0, limit: int = 100) -> list[Coupon]:
    return db.query(Coupon).order_by(Coupon.id.desc()).offset(skip).limit(limit).all()


# ── Lấy 1 theo id ────────────────────────────────────────────────────────────
def get_coupon(db: Session, coupon_id: int) -> Optional[Coupon]:
    return db.get(Coupon, coupon_id)


# ── Lấy 1 theo code (không phân biệt hoa thường) ────────────────────────────
def get_coupon_by_code(db: Session, code: str) -> Optional[Coupon]:
    return db.query(Coupon).filter(Coupon.code == code.strip().upper()).first()


# ── Tạo mới ──────────────────────────────────────────────────────────────────
def create_coupon(db: Session, data: CouponCreate) -> Coupon:
    existing = get_coupon_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Mã giảm giá '{data.code}' đã tồn tại")

    coupon = Coupon(
        code=data.code,
        description=data.description,
        discount_type=data.discount_type.value,
        discount_value=data.discount_value,
        min_order_amount=data.min_order_amount,
        max_uses=data.max_uses,
        used_count=0,
        valid_from=data.valid_from,
        valid_to=data.valid_to,
        status="ACTIVE",
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


# ── Cập nhật ─────────────────────────────────────────────────────────────────
def update_coupon(db: Session, coupon: Coupon, data: CouponUpdate) -> Coupon:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "discount_type" and value is not None:
            value = value.value
        if field == "status" and value is not None:
            value = value.value
        setattr(coupon, field, value)
    db.commit()
    db.refresh(coupon)
    return coupon


# ── Ngừng mã (soft-stop) ──────────────────────────────────────────────────────
def deactivate_coupon(db: Session, coupon: Coupon) -> Coupon:
    coupon.status = "INACTIVE"
    db.commit()
    db.refresh(coupon)
    return coupon


# ── Kiểm tra mã hợp lệ, trả về số tiền giảm ────────────────────────────────
def validate_and_get_discount(
    db: Session,
    code: str,
    order_amount: Decimal,
) -> tuple[Coupon, Decimal]:
    """Kiểm tra mã giảm giá:
    - Mã tồn tại
    - Trạng thái ACTIVE
    - Chưa hết hạn (valid_from / valid_to)
    - Còn lượt dùng
    - Đủ đơn tối thiểu

    Trả về (coupon, discount_amount).
    Ném HTTPException với mô tả rõ ràng nếu không hợp lệ.
    """
    coupon = get_coupon_by_code(db, code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Mã giảm giá không tồn tại")

    if coupon.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Mã giảm giá đã ngừng hoạt động")

    now = datetime.now()
    if coupon.valid_from and now < coupon.valid_from:
        raise HTTPException(status_code=400, detail="Mã giảm giá chưa đến thời gian áp dụng")

    if coupon.valid_to and now > coupon.valid_to:
        raise HTTPException(status_code=400, detail="Mã giảm giá đã hết hạn")

    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        raise HTTPException(status_code=400, detail="Mã giảm giá đã hết lượt sử dụng")

    min_amount = Decimal(coupon.min_order_amount)
    if order_amount < min_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Đơn hàng chưa đạt giá trị tối thiểu {int(min_amount):,}đ để áp dụng mã",
        )

    # Tính số tiền giảm thực tế
    discount_value = Decimal(coupon.discount_value)
    if coupon.discount_type == "PERCENT":
        discount_amount = (order_amount * discount_value / 100).quantize(Decimal("1"))
    else:
        discount_amount = min(discount_value, order_amount)

    return coupon, discount_amount


# ── Trừ lượt dùng (gọi sau khi đặt hàng thành công) ─────────────────────────
def increment_used_count(db: Session, coupon: Coupon) -> None:
    coupon.used_count = coupon.used_count + 1
    db.add(coupon)
    # Không commit ở đây — để caller (order_service) commit cùng transaction

