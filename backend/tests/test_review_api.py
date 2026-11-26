"""Unit test cho API đánh giá món:
- Khách có thể đánh giá trực tiếp hoặc gắn với đơn đã hoàn thành;
- Đánh giá theo đơn chỉ chấm từng món một lần;
- Chặn khi đơn chưa hoàn thành;
- Chặn đánh giá 2 lần cùng 1 món;
- Điểm trung bình của món;
- Cửa hàng trả lời đánh giá;
- Admin ẩn đánh giá vi phạm.
"""
import asyncio
import os
import sys
import unittest
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers

from app.crud import review as review_crud
from app.db.base import Base
from app.models.category import Category
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish
from app.models.order import Order, OrderItem
from app.models.review import Review
from app.models.user import User
from app.routers import reviews as review_router
from app.schemas.review import ReviewCreate, ReviewReplyRequest


class TestReviewAPI(unittest.TestCase):
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
        self._init_data()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def _init_data(self):
        # Tạo user khách
        self.user = User(
            id=1,
            full_name="Khách Hàng Test",
            email="khach@example.com",
            password_hash="pwd",
            role="CUSTOMER",
        )
        self.db.add(self.user)

        # Tạo khu vực & món ăn
        self.area = DeliveryArea(id=1, name="Quận 1", shipping_fee=Decimal("15000"), is_active=True)
        self.db.add(self.area)

        self.dish1 = Dish(id=1, name="Mì trộn gà sốt", price=Decimal("45000"), is_available=True)
        self.dish2 = Dish(id=2, name="Trà sữa thái xanh", price=Decimal("25000"), is_available=True)
        self.db.add_all([self.dish1, self.dish2])

        # Đơn 1: Đã COMPLETED
        self.order_completed = Order(
            id=1,
            order_code="DH001",
            user_id=1,
            recipient_name="Khách Hàng Test",
            recipient_phone="0901234567",
            delivery_address="123 Phố",
            delivery_area_id=1,
            subtotal=Decimal("70000"),
            total_amount=Decimal("85000"),
            payment_method="COD",
            status="COMPLETED",
        )
        # Đơn 2: Đang PENDING
        self.order_pending = Order(
            id=2,
            order_code="DH002",
            user_id=1,
            recipient_name="Khách Hàng Test",
            recipient_phone="0901234567",
            delivery_address="123 Phố",
            delivery_area_id=1,
            subtotal=Decimal("45000"),
            total_amount=Decimal("60000"),
            payment_method="COD",
            status="PENDING",
        )
        self.db.add_all([self.order_completed, self.order_pending])
        self.db.commit()

    def test_review_completed_order_success(self):
        """Khách có đơn Hoàn thành được chấm sao, nhận xét và ảnh."""
        payload = ReviewCreate(
            order_id=1,
            dish_id=1,
            user_id=1,
            rating=5,
            content="Mì ăn rất đậm đà, nóng hổi!",
            image_url="https://example.com/mi.jpg",
        )
        review = review_crud.create_review(self.db, payload)
        self.assertIsNotNone(review.id)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.content, "Mì ăn rất đậm đà, nóng hổi!")
        self.assertEqual(review.image_url, "https://example.com/mi.jpg")
        self.assertFalse(review.is_hidden)

    def test_review_without_order_success(self):
        """Khách có thể đánh giá món trực tiếp từ trang chi tiết."""
        review = review_crud.create_review(
            self.db,
            ReviewCreate(
                dish_id=1,
                rating=4,
                content="Món ngon, sẽ gọi lại.",
            ),
        )

        self.assertIsNone(review.order_id)
        self.assertIsNone(review.user_id)
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.content, "Món ngon, sẽ gọi lại.")

    def test_review_blocked_when_order_not_completed(self):
        """Chặn đánh giá khi đơn chưa Hoàn thành."""
        payload = ReviewCreate(
            order_id=2,  # PENDING
            dish_id=1,
            user_id=1,
            rating=4,
            content="Giao hơi chậm",
        )
        with self.assertRaises(HTTPException) as ctx:
            review_crud.create_review(self.db, payload)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("hoàn thành", ctx.exception.detail.lower())

    def test_review_duplicate_dish_blocked(self):
        """Mỗi món trong đơn chỉ được đánh giá một lần."""
        payload = ReviewCreate(
            order_id=1,
            dish_id=1,
            user_id=1,
            rating=5,
            content="Lần 1",
        )
        review_crud.create_review(self.db, payload)

        # Đánh giá lại cùng món trong đơn đó
        payload2 = ReviewCreate(
            order_id=1,
            dish_id=1,
            user_id=1,
            rating=4,
            content="Lần 2",
        )
        with self.assertRaises(HTTPException) as ctx:
            review_crud.create_review(self.db, payload2)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("đã được đánh giá", ctx.exception.detail.lower())

    def test_average_rating_and_hide_review(self):
        """Kiểm tra điểm trung bình của món và chức năng ẩn đánh giá vi phạm."""
        # Tạo thêm 1 order completed khác của user 1 để đánh giá dish 1 thêm lần nữa
        order2 = Order(
            id=3,
            order_code="DH003",
            user_id=1,
            recipient_name="Khách Hàng Test",
            recipient_phone="0901234567",
            delivery_address="123 Phố",
            delivery_area_id=1,
            subtotal=Decimal("45000"),
            total_amount=Decimal("60000"),
            payment_method="COD",
            status="COMPLETED",
        )
        self.db.add(order2)
        self.db.commit()

        # Review 1: 5 sao
        r1 = review_crud.create_review(
            self.db,
            ReviewCreate(order_id=1, dish_id=1, user_id=1, rating=5, content="Ngon"),
        )
        # Review 2: 3 sao
        r2 = review_crud.create_review(
            self.db,
            ReviewCreate(order_id=3, dish_id=1, user_id=1, rating=3, content="Bình thường"),
        )

        # Trung bình = (5 + 3) / 2 = 4.0
        summary = review_crud.get_dish_reviews(self.db, dish_id=1)
        self.assertEqual(summary["total_reviews"], 2)
        self.assertEqual(summary["average_rating"], 4.0)

        # Admin ẩn r2 vì vi phạm
        review_crud.set_review_hidden(self.db, review_id=r2.id, is_hidden=True)

        # Sau khi ẩn r2: chỉ còn r1 (5 sao), avg = 5.0
        summary_after = review_crud.get_dish_reviews(self.db, dish_id=1)
        self.assertEqual(summary_after["total_reviews"], 1)
        self.assertEqual(summary_after["average_rating"], 5.0)

    def test_shop_reply_to_review(self):
        """Cửa hàng trả lời đánh giá."""
        r = review_crud.create_review(
            self.db,
            ReviewCreate(order_id=1, dish_id=2, user_id=1, rating=4, content="Trà thơm"),
        )
        replied = review_crud.reply_to_review(
            self.db,
            review_id=r.id,
            data=ReviewReplyRequest(reply="Cảm ơn bạn đã thưởng thức ạ!"),
        )
        self.assertEqual(replied.shop_reply, "Cảm ơn bạn đã thưởng thức ạ!")
        self.assertIsNotNone(replied.replied_at)

    def test_upload_review_image_saves_valid_png(self):
        image_bytes = b"\x89PNG\r\n\x1a\nvalid image data"
        upload = UploadFile(
            filename="review.png",
            file=BytesIO(image_bytes),
            headers=Headers({"content-type": "image/png"}),
        )

        with TemporaryDirectory() as upload_dir:
            with patch.object(review_router, "UPLOAD_DIR", Path(upload_dir)):
                result = asyncio.run(review_router.upload_review_image(upload))

            self.assertTrue(result["image_url"].startswith("/uploads/reviews/"))
            saved_file = Path(upload_dir) / Path(result["image_url"]).name
            self.assertEqual(saved_file.read_bytes(), image_bytes)

    def test_upload_review_image_rejects_invalid_image_content(self):
        upload = UploadFile(
            filename="review.png",
            file=BytesIO(b"not an image"),
            headers=Headers({"content-type": "image/png"}),
        )

        with TemporaryDirectory() as upload_dir:
            with patch.object(review_router, "UPLOAD_DIR", Path(upload_dir)):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(review_router.upload_review_image(upload))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("không phải ảnh hợp lệ", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()

