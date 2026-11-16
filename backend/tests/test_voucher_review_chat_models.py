"""Unit test cho Task [Database] Model mã giảm giá, đánh giá và tin nhắn:
- Model Voucher (mã, kiểu % hoặc số tiền, giá trị, đơn tối thiểu, giảm tối đa, hạn dùng, số lượt, đã dùng) + schema
- Model Review (đơn, món, số sao, nội dung, ảnh, trả lời của cửa hàng) + schema
- Model ChatMessage (khách, người gửi, nội dung, đã đọc, thời điểm) + schema
"""
import sys
import os
import unittest
from datetime import datetime, timezone
from decimal import Decimal

# Đảm bảo import được app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.chat_message import ChatMessage
from app.models.coupon import Coupon
from app.models.dish import Dish
from app.models.order import Order
from app.models.review import Review
from app.models.user import User
from app.models.voucher import Voucher
from app.schemas.chat_message import ChatMessageCreate, ChatMessageResponse
from app.schemas.coupon import CouponCreate, CouponResponse
from app.schemas.review import ReviewCreate, ReviewResponse
from app.schemas.voucher import VoucherCreate, VoucherResponse


class TestVoucherReviewChatModels(unittest.TestCase):
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

    def test_voucher_model_and_schema(self):
        """Kiểm tra Model Voucher và Schema theo đúng yêu cầu đề bài."""
        # 1. Kiểm tra Schema
        v_create = VoucherCreate(
            code="GIAM50K",
            discount_type="FIXED",
            discount_value=Decimal("50000"),
            min_order_amount=Decimal("150000"),
            max_discount_amount=Decimal("50000"),
            max_uses=20,
        )
        self.assertEqual(v_create.code, "GIAM50K")
        self.assertEqual(v_create.discount_type, "FIXED")

        # 2. Kiểm tra lưu vào database
        voucher = Voucher(
            code=v_create.code,
            discount_type=v_create.discount_type,
            discount_value=v_create.discount_value,
            min_order_amount=v_create.min_order_amount,
            max_discount_amount=v_create.max_discount_amount,
            max_uses=v_create.max_uses,
            used_count=0,
            status="ACTIVE",
        )
        self.db.add(voucher)
        self.db.commit()
        self.db.refresh(voucher)

        self.assertIsNotNone(voucher.id)
        self.assertEqual(voucher.code, "GIAM50K")
        self.assertEqual(voucher.used_count, 0)
        self.assertEqual(voucher.status, "ACTIVE")

        # 3. Kiểm tra serialization sang VoucherResponse
        v_res = VoucherResponse.model_validate(voucher)
        self.assertEqual(v_res.id, voucher.id)
        self.assertEqual(v_res.code, "GIAM50K")

    def test_review_model_and_schema(self):
        """Kiểm tra Model Review và Schema (đơn, món, số sao, nội dung, ảnh, trả lời)."""
        review = Review(
            order_id=10,
            dish_id=5,
            user_id=1,
            rating=5,
            content="Món ăn rất ngon, giao nhanh!",
            image_url="https://example.com/photo.jpg",
            shop_reply="Cảm ơn bạn đã ủng hộ shop!",
            replied_at=datetime.now(timezone.utc),
            is_hidden=False,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)

        self.assertIsNotNone(review.id)
        self.assertEqual(review.order_id, 10)
        self.assertEqual(review.dish_id, 5)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.content, "Món ăn rất ngon, giao nhanh!")
        self.assertEqual(review.shop_reply, "Cảm ơn bạn đã ủng hộ shop!")
        self.assertFalse(review.is_hidden)

        # Kiểm tra Schema
        r_res = ReviewResponse.model_validate(review)
        self.assertEqual(r_res.id, review.id)
        self.assertEqual(r_res.rating, 5)
        self.assertEqual(r_res.shop_reply, "Cảm ơn bạn đã ủng hộ shop!")

    def test_chat_message_model_and_schema(self):
        """Kiểm tra Model ChatMessage và Schema (khách, người gửi, nội dung, đã đọc, thời điểm)."""
        chat = ChatMessage(
            customer_id=1,
            sender_id=1,
            content="Quán có giao hàng qua khung giờ 12h đêm không ạ?",
            is_read=False,
        )
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)

        self.assertIsNotNone(chat.id)
        self.assertEqual(chat.customer_id, 1)
        self.assertEqual(chat.sender_id, 1)
        self.assertEqual(chat.content, "Quán có giao hàng qua khung giờ 12h đêm không ạ?")
        self.assertFalse(chat.is_read)
        self.assertIsNotNone(chat.sent_at)

        # Kiểm tra Schema
        c_res = ChatMessageResponse.model_validate(chat)
        self.assertEqual(c_res.id, chat.id)
        self.assertEqual(c_res.content, chat.content)
        self.assertFalse(c_res.is_read)


if __name__ == "__main__":
    unittest.main()

