"""Script kiểm thử toàn bộ yêu cầu của task: [Khuyến mãi] API mã giảm giá.
Chạy:
    python backend/tests/test_coupon_api.py
"""
from datetime import datetime, timedelta
from decimal import Decimal
import os
from pathlib import Path
import sys
import unittest

# Đảm bảo import được package app khi chạy từ bất kỳ thư mục nào
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.models.coupon import Coupon
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish
from app.models.user import User
from app.routers.coupons import (
    apply_coupon,
    create_coupon,
    deactivate_coupon,
    get_coupon,
    list_coupons,
    update_coupon,
)
from app.schemas.coupon import (
    CouponApplyRequest,
    CouponCreate,
    CouponStatus,
    CouponUpdate,
    DiscountType,
)
from app.schemas.order import OrderCreate, OrderItemCreate, PaymentMethod
from app.services import order_service


class CouponTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        self.seed_data()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def seed_data(self):
        user = User(
            id=1,
            full_name="Khách Hàng Test",
            email="test@example.com",
            phone="0901112222",
            password_hash="hash",
            role="CUSTOMER",
            is_active=True,
        )
        self.db.add(user)

        area = DeliveryArea(
            id=1,
            name="Khu Vực 1",
            shipping_fee=Decimal("15000"),
            is_active=True,
        )
        self.db.add(area)

        dish = Dish(
            id=1,
            name="Mì Xào Bò",
            price=Decimal("50000"),
            is_available=True,
            is_active=True,
            status="AVAILABLE",
        )
        self.db.add(dish)
        self.db.commit()

    # ────────────────────────────────────────────────────────────
    # 1. ADMIN TẠO MÃ
    # ────────────────────────────────────────────────────────────
    def test_admin_create_coupon_fixed_success(self):
        data = CouponCreate(
            code="giam20k",  # Chữ thường -> tự uppercase
            description="Giảm 20k cho đơn từ 50k",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("20000"),
            min_order_amount=Decimal("50000"),
            max_uses=10,
        )
        res = create_coupon(data=data, db=self.db)
        self.assertEqual(res.code, "GIAM20K")
        self.assertEqual(res.discount_value, Decimal("20000"))
        self.assertEqual(res.status, "ACTIVE")

    def test_admin_create_coupon_percent_success(self):
        data = CouponCreate(
            code="SALE15",
            description="Giảm 15%",
            discount_type=DiscountType.PERCENT,
            discount_value=Decimal("15"),
            min_order_amount=Decimal("0"),
        )
        res = create_coupon(data=data, db=self.db)
        self.assertEqual(res.code, "SALE15")
        self.assertEqual(res.discount_type, "PERCENT")

    def test_admin_create_coupon_duplicate_code(self):
        data = CouponCreate(
            code="DUPLICATE",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("10000"),
        )
        create_coupon(data=data, db=self.db)

        with self.assertRaises(HTTPException) as ctx:
            create_coupon(data=data, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("đã tồn tại", ctx.exception.detail)

    def test_admin_create_coupon_percent_exceeds_100(self):
        with self.assertRaises(ValueError):
            CouponCreate(
                code="OVER100",
                discount_type=DiscountType.PERCENT,
                discount_value=Decimal("150"),
            )

    # ────────────────────────────────────────────────────────────
    # 2. ADMIN SỬA & NGỪNG MÃ
    # ────────────────────────────────────────────────────────────
    def test_admin_update_and_deactivate_coupon(self):
        coupon = Coupon(
            code="TESTUPDATE",
            discount_type="FIXED",
            discount_value=Decimal("10000"),
            min_order_amount=Decimal("30000"),
            max_uses=5,
            used_count=0,
            status="ACTIVE",
        )
        self.db.add(coupon)
        self.db.commit()

        # Sửa mã
        updated = update_coupon(
            data=CouponUpdate(description="Mô tả mới", min_order_amount=Decimal("40000")),
            coupon=coupon,
            db=self.db,
        )
        self.assertEqual(updated.description, "Mô tả mới")
        self.assertEqual(updated.min_order_amount, Decimal("40000"))

        # Ngừng mã (deactivate)
        deactivated = deactivate_coupon(coupon=coupon, db=self.db)
        self.assertEqual(deactivated.status, "INACTIVE")

        # Ngừng lần 2 sẽ báo lỗi 400
        with self.assertRaises(HTTPException) as ctx:
            deactivate_coupon(coupon=coupon, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)

    # ────────────────────────────────────────────────────────────
    # 3. API KIỂM TRA MÃ (Giỏ hàng)
    # ────────────────────────────────────────────────────────────
    def test_apply_coupon_case_insensitive_and_calculation(self):
        coupon = Coupon(
            code="GIAM10K",
            discount_type="FIXED",
            discount_value=Decimal("10000"),
            min_order_amount=Decimal("40000"),
            status="ACTIVE",
        )
        self.db.add(coupon)
        self.db.commit()

        # Áp dụng với chữ thường "giam10k"
        req = CouponApplyRequest(code="giam10k", order_amount=Decimal("50000"))
        res = apply_coupon(data=req, db=self.db)
        self.assertEqual(res.code, "GIAM10K")
        self.assertEqual(res.discount_amount, Decimal("10000"))

    def test_apply_coupon_percent(self):
        coupon = Coupon(
            code="SALE20",
            discount_type="PERCENT",
            discount_value=Decimal("20"),
            min_order_amount=Decimal("0"),
            status="ACTIVE",
        )
        self.db.add(coupon)
        self.db.commit()

        # Đơn 100.000đ giảm 20% = 20.000đ
        req = CouponApplyRequest(code="Sale20", order_amount=Decimal("100000"))
        res = apply_coupon(data=req, db=self.db)
        self.assertEqual(res.discount_amount, Decimal("20000"))

    def test_apply_coupon_min_order_amount_not_met(self):
        coupon = Coupon(
            code="MIN100K",
            discount_type="FIXED",
            discount_value=Decimal("15000"),
            min_order_amount=Decimal("100000"),
            status="ACTIVE",
        )
        self.db.add(coupon)
        self.db.commit()

        req = CouponApplyRequest(code="MIN100K", order_amount=Decimal("50000"))
        with self.assertRaises(HTTPException) as ctx:
            apply_coupon(data=req, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("tối thiểu", ctx.exception.detail)

    def test_apply_coupon_expired(self):
        past = datetime.now() - timedelta(days=2)
        coupon = Coupon(
            code="HETHAN",
            discount_type="FIXED",
            discount_value=Decimal("10000"),
            min_order_amount=Decimal("0"),
            valid_to=past,
            status="ACTIVE",
        )
        self.db.add(coupon)
        self.db.commit()

        req = CouponApplyRequest(code="HETHAN", order_amount=Decimal("50000"))
        with self.assertRaises(HTTPException) as ctx:
            apply_coupon(data=req, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("hết hạn", ctx.exception.detail)

    def test_apply_coupon_max_uses_reached(self):
        coupon = Coupon(
            code="HETLUOT",
            discount_type="FIXED",
            discount_value=Decimal("10000"),
            min_order_amount=Decimal("0"),
            max_uses=2,
            used_count=2,
            status="ACTIVE",
        )
        self.db.add(coupon)
        self.db.commit()

        req = CouponApplyRequest(code="HETLUOT", order_amount=Decimal("50000"))
        with self.assertRaises(HTTPException) as ctx:
            apply_coupon(data=req, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("hết lượt", ctx.exception.detail)

    def test_apply_coupon_inactive(self):
        coupon = Coupon(
            code="NGUNGHOATDONG",
            discount_type="FIXED",
            discount_value=Decimal("10000"),
            min_order_amount=Decimal("0"),
            status="INACTIVE",
        )
        self.db.add(coupon)
        self.db.commit()

        req = CouponApplyRequest(code="NGUNGHOATDONG", order_amount=Decimal("50000"))
        with self.assertRaises(HTTPException) as ctx:
            apply_coupon(data=req, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("ngừng hoạt động", ctx.exception.detail)

    # ────────────────────────────────────────────────────────────
    # 4. TRỪ LƯỢT KHI ĐẶT MÓN THÀNH CÔNG
    # ────────────────────────────────────────────────────────────
    def test_create_order_with_coupon_decrements_uses(self):
        coupon = Coupon(
            code="GIAM10K",
            discount_type="FIXED",
            discount_value=Decimal("10000"),
            min_order_amount=Decimal("40000"),
            max_uses=2,
            used_count=0,
            status="ACTIVE",
        )
        self.db.add(coupon)
        self.db.commit()

        # Đặt món: 1 mì xào bò giá 50.000đ + ship 15.000đ - giảm 10.000đ = 55.000đ
        order_create = OrderCreate(
            recipient_name="Người Nhận",
            recipient_phone="0909999999",
            delivery_address="123 Đường ABC",
            delivery_area_id=1,
            payment_method=PaymentMethod.COD,
            coupon_code="giam10k",  # gửi chữ thường
            items=[OrderItemCreate(dish_id=1, quantity=1, selected_options=[])],
        )

        order1 = order_service.create_order_for_user(self.db, user_id=1, data=order_create)
        self.assertEqual(order1.coupon_code, "GIAM10K")
        self.assertEqual(order1.discount_amount, Decimal("10000"))
        self.assertEqual(order1.total_amount, Decimal("55000"))

        # Kiểm tra used_count trong database đã tăng lên 1
        self.db.refresh(coupon)
        self.assertEqual(coupon.used_count, 1)

        # Đặt món lần 2 -> used_count lên 2
        order2 = order_service.create_order_for_user(self.db, user_id=1, data=order_create)
        self.assertEqual(order2.coupon_code, "GIAM10K")
        self.db.refresh(coupon)
        self.assertEqual(coupon.used_count, 2)

        # Đặt món lần 3 -> mã đã hết lượt (max_uses=2, used_count=2) -> báo lỗi 400
        with self.assertRaises(HTTPException) as ctx:
            order_service.create_order_for_user(self.db, user_id=1, data=order_create)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("hết lượt", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
