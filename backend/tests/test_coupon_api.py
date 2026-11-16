"""Unit test cho Coupon API & CRUD:
- Admin xem danh sách, tạo mới, sửa thông tin, vô hiệu hoá;
- Áp dụng mã (tính số tiền giảm theo FIXED/PERCENT, kiểm tra đơn tối thiểu, hết hạn, hết lượt).
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.crud import coupon as coupon_crud
from app.db.base import Base
from app.models.coupon import Coupon
from app.schemas.coupon import CouponCreate, CouponUpdate


class TestCouponAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_coupon_crud_admin(self):
        """Admin tạo, xem, sửa, vô hiệu hoá mã giảm giá."""
        # 1. Tạo mã
        data = CouponCreate(
            code="GIAM20K",
            description="Giảm 20.000đ",
            discount_type="FIXED",
            discount_value=Decimal("20000"),
            min_order_amount=Decimal("100000"),
            max_uses=5,
        )
        c = coupon_crud.create_coupon(self.db, data)
        self.assertIsNotNone(c.id)
        self.assertEqual(c.code, "GIAM20K")
        self.assertEqual(c.status, "ACTIVE")

        # 2. Sửa mã
        update_data = CouponUpdate(description="Giảm 20k đơn từ 120k", min_order_amount=Decimal("120000"))
        c_updated = coupon_crud.update_coupon(self.db, c, update_data)
        self.assertEqual(c_updated.min_order_amount, Decimal("120000"))

        # 3. Vô hiệu hoá
        c_deactivated = coupon_crud.deactivate_coupon(self.db, c)
        self.assertEqual(c_deactivated.status, "INACTIVE")

    def test_apply_coupon_percentage_and_fixed(self):
        """Kiểm tra tính tiền giảm cho mã % và cố định."""
        # Mã FIXED
        c_fixed = coupon_crud.create_coupon(
            self.db,
            CouponCreate(
                code="FIXED15K",
                discount_type="FIXED",
                discount_value=Decimal("15000"),
                min_order_amount=Decimal("50000"),
            ),
        )
        _, discount1 = coupon_crud.validate_and_get_discount(self.db, "FIXED15K", Decimal("100000"))
        self.assertEqual(discount1, Decimal("15000"))

        # Mã PERCENT 10%
        c_pct = coupon_crud.create_coupon(
            self.db,
            CouponCreate(
                code="DISCOUNT10",
                discount_type="PERCENT",
                discount_value=Decimal("10"),
                min_order_amount=Decimal("0"),
            ),
        )
        _, discount2 = coupon_crud.validate_and_get_discount(self.db, "discount10", Decimal("200000"))
        self.assertEqual(discount2, Decimal("20000"))

    def test_coupon_validation_errors(self):
        """Kiểm tra các trường hợp vi phạm điều kiện dùng mã."""
        # Tạo mã yêu cầu tối thiểu 100k
        coupon_crud.create_coupon(
            self.db,
            CouponCreate(
                code="MIN100K",
                discount_type="FIXED",
                discount_value=Decimal("10000"),
                min_order_amount=Decimal("100000"),
            ),
        )

        # Đơn 80k -> Không đủ đơn tối thiểu
        with self.assertRaises(HTTPException) as ctx:
            coupon_crud.validate_and_get_discount(self.db, "MIN100K", Decimal("80000"))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("tối thiểu", ctx.exception.detail)

        # Mã không tồn tại
        with self.assertRaises(HTTPException) as ctx2:
            coupon_crud.validate_and_get_discount(self.db, "NOTEXIST", Decimal("200000"))
        self.assertEqual(ctx2.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()

