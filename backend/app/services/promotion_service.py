"""Module Khuyến mãi: Tính số tiền giảm giá (discount_amount) ở server."""
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.crud import coupon as coupon_crud

# Một số mã khuyến mãi có sẵn để phục vụ kiểm thử khi bảng coupons/vouchers chưa có mã đó
BUILTIN_VOUCHERS: dict[str, dict] = {
    "GIAM10": {
        "type": "PERCENT",
        "value": Decimal("10"),
        "max_discount": Decimal("50000"),
        "min_order_value": Decimal("0"),
    },
    "GIAM20K": {
        "type": "FIXED",
        "value": Decimal("20000"),
        "max_discount": None,
        "min_order_value": Decimal("50000"),
    },
    "FREESHIP": {
        "type": "FREESHIP",
        "value": Decimal("0"),
        "max_discount": Decimal("30000"),
        "min_order_value": Decimal("0"),
    },
}


def calculate_discount(
    db: Session,
    subtotal: Decimal,
    shipping_fee: Decimal = Decimal("0"),
    voucher_code: str | None = None,
) -> Decimal:
    """Hàm của module Khuyến mãi: tính số tiền giảm giá ở server dựa trên tạm tính và mã giảm giá."""
    if not voucher_code or not voucher_code.strip() or subtotal <= 0:
        return Decimal("0")

    code = voucher_code.strip().upper()

    bind = db.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    # 1. Kiểm tra trong bảng coupons (nếu mã tồn tại trong bảng coupons)
    if "coupons" in table_names:
        coupon_obj = coupon_crud.get_coupon_by_code(db, code)
        if coupon_obj is not None:
            _, discount_amt = coupon_crud.validate_and_get_discount(db, code, subtotal)
            return min(Decimal(str(discount_amt)), subtotal + shipping_fee)

    # 2. Kiểm tra trong bảng vouchers (nếu có)
    if "vouchers" in table_names:
        row = db.execute(
            text("SELECT * FROM vouchers WHERE UPPER(code) = :code LIMIT 1"),
            {"code": code},
        ).mappings().first()
        if row is not None:
            if not row.get("is_active", 1):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mã giảm giá '{code}' đã hết hiệu lực",
                )
            min_order = Decimal(str(row.get("min_order_value") or row.get("min_order_amount") or 0))
            if subtotal < min_order:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Đơn tối thiểu {int(min_order):,}đ mới áp dụng được mã '{code}'",
                )
            discount_type = str(row.get("discount_type") or row.get("type") or "FIXED").upper()
            val = Decimal(str(row.get("discount_value") or row.get("value") or 0))
            if discount_type in ("PERCENT", "PERCENTAGE"):
                discount = (subtotal * val) / Decimal("100")
            else:
                discount = val
            max_disc = row.get("max_discount") or row.get("max_discount_amount")
            if max_disc is not None:
                discount = min(discount, Decimal(str(max_disc)))
            return min(discount, subtotal + shipping_fee)

    # 3. Kiểm tra trong danh sách mã khuyến mãi mẫu (GIAM10, GIAM20K, FREESHIP)
    voucher = BUILTIN_VOUCHERS.get(code)
    if voucher is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã giảm giá '{code}' không hợp lệ hoặc không tồn tại",
        )

    min_order = voucher["min_order_value"]
    if subtotal < min_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tạm tính tối thiểu {int(min_order):,}đ mới áp dụng được mã '{code}'",
        )

    v_type = voucher["type"]
    if v_type == "PERCENT":
        discount = (subtotal * voucher["value"]) / Decimal("100")
    elif v_type == "FREESHIP":
        discount = shipping_fee
    else:
        discount = voucher["value"]

    if voucher["max_discount"] is not None:
        discount = min(discount, voucher["max_discount"])

    return min(discount, subtotal + shipping_fee)
