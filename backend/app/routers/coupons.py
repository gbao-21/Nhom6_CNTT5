"""API mã giảm giá: /api/coupons

Phân quyền đơn giản (chưa có middleware auth thực sự):
- GET  /api/coupons/apply  → Public, dùng cho module Giỏ hàng
- Các route còn lại        → Admin (truyền role=ADMIN qua query hoặc header để test)
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import coupon as coupon_crud
from app.db.session import get_db
from app.schemas.coupon import (
    CouponApplyRequest,
    CouponApplyResponse,
    CouponCreate,
    CouponResponse,
    CouponUpdate,
)

router = APIRouter(prefix="/coupons", tags=["Coupons"])


# ── Helper ────────────────────────────────────────────────────────────────────
def get_coupon_or_404(coupon_id: int, db: Session = Depends(get_db)):
    coupon = coupon_crud.get_coupon(db, coupon_id)
    if coupon is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy mã giảm giá id={coupon_id}")
    return coupon


def require_admin(role: str = Query(default="ADMIN", description="Vai trò người dùng (ADMIN)")):
    """Dependency kiểm tra quyền Admin đơn giản qua query param."""
    if role.upper() not in ("ADMIN", "STAFF"):
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền thực hiện thao tác này")


# ── Public: Kiểm tra & áp dụng mã từ Giỏ hàng ───────────────────────────────
@router.post(
    "/apply",
    response_model=CouponApplyResponse,
    summary="Kiểm tra mã giảm giá (dùng cho module Giỏ hàng)",
)
def apply_coupon(data: CouponApplyRequest, db: Session = Depends(get_db)):
    """Kiểm tra mã giảm giá:
    - Còn hạn, còn lượt, đủ đơn tối thiểu
    - Trả về số tiền giảm thực tế
    - Mã không phân biệt hoa thường
    """
    coupon, discount_amount = coupon_crud.validate_and_get_discount(
        db, data.code, data.order_amount
    )
    return CouponApplyResponse(
        code=coupon.code,
        discount_type=coupon.discount_type,
        discount_value=Decimal(coupon.discount_value),
        discount_amount=discount_amount,
        message=f"Áp dụng mã thành công! Giảm {int(discount_amount):,}đ",
    )


# ── Admin: Danh sách mã ───────────────────────────────────────────────────────
@router.get(
    "",
    response_model=list[CouponResponse],
    summary="[Admin] Xem danh sách mã giảm giá",
    dependencies=[Depends(require_admin)],
)
def list_coupons(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return coupon_crud.get_coupons(db, skip=skip, limit=limit)


# ── Admin: Chi tiết 1 mã ─────────────────────────────────────────────────────
@router.get(
    "/{coupon_id}",
    response_model=CouponResponse,
    summary="[Admin] Xem chi tiết mã giảm giá",
    dependencies=[Depends(require_admin)],
)
def get_coupon(coupon=Depends(get_coupon_or_404)):
    return coupon


# ── Admin: Tạo mã mới ────────────────────────────────────────────────────────
@router.post(
    "",
    response_model=CouponResponse,
    status_code=201,
    summary="[Admin] Tạo mã giảm giá mới",
    dependencies=[Depends(require_admin)],
)
def create_coupon(data: CouponCreate, db: Session = Depends(get_db)):
    return coupon_crud.create_coupon(db, data)


# ── Admin: Sửa mã ────────────────────────────────────────────────────────────
@router.patch(
    "/{coupon_id}",
    response_model=CouponResponse,
    summary="[Admin] Sửa thông tin mã giảm giá",
    dependencies=[Depends(require_admin)],
)
def update_coupon(
    data: CouponUpdate,
    coupon=Depends(get_coupon_or_404),
    db: Session = Depends(get_db),
):
    return coupon_crud.update_coupon(db, coupon, data)


# ── Admin: Ngừng mã ──────────────────────────────────────────────────────────
@router.patch(
    "/{coupon_id}/deactivate",
    response_model=CouponResponse,
    summary="[Admin] Ngừng hoạt động mã giảm giá",
    dependencies=[Depends(require_admin)],
)
def deactivate_coupon(coupon=Depends(get_coupon_or_404), db: Session = Depends(get_db)):
    if coupon.status == "INACTIVE":
        raise HTTPException(status_code=400, detail="Mã giảm giá đã ở trạng thái ngừng hoạt động")
    return coupon_crud.deactivate_coupon(db, coupon)

