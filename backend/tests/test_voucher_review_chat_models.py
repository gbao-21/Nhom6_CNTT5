"""Script kiểm thử toàn bộ yêu cầu của task:
[Database] Model mã giảm giá, đánh giá và tin nhắn:
1. Model Voucher & Schema Voucher:
   - Các trường: mã, kiểu % hoặc số tiền, giá trị, đơn tối thiểu, giảm tối đa, hạn dùng, số lượt, đã dùng.
   - Pydantic schema validation.
2. Model Review & Schema Review:
   - Các trường: đơn (order_id), món (dish_id), số sao (rating), nội dung (content), ảnh (image_url), trả lời của cửa hàng (shop_reply, replied_at).
   - Relationship đến Order, Dish, User.
3. Model ChatMessage & Schema ChatMessage:
   - Các trường: khách (customer_id), người gửi (sender_id), nội dung (content), đã đọc (is_read), thời điểm (created_at).
   - Relationship đến User (customer, sender).
"""
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys
import unittest

# Đảm bảo import được backend app
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.models.chat_message import ChatMessage
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish
from app.models.order import Order
from app.models.review import Review
from app.models.user import User
from app.models.voucher import Voucher
from app.schemas.chat_message import (
    ChatMessageCreate,
    ChatMessageMarkRead,
    ChatMessageResponse,
)
from app.schemas.review import (
    ReviewCreate,
    ReviewReplyRequest,
    ReviewResponse,
    ReviewUpdate,
)
from app.schemas.voucher import (
    VoucherCreate,
    VoucherDiscountType,
    VoucherResponse,
    VoucherStatus,
    VoucherUpdate,
)


class DatabaseModelsAndSchemasTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        self.seed_base_data()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def seed_base_data(self):
        # 1. Users
        self.customer = User(
            id=1,
            full_name="Khách Hàng A",
            email="customer@example.com",
            phone="0901234567",
            password_hash="pw_hash_1",
            role="CUSTOMER",
            is_active=True,
        )
        self.staff = User(
            id=2,
            full_name="Nhân Viên B",
            email="staff@example.com",
            phone="0909876543",
            password_hash="pw_hash_2",
            role="STAFF",
            is_active=True,
        )
        self.db.add_all([self.customer, self.staff])

        # 2. Delivery Area
        self.area = DeliveryArea(
            id=1,
            name="Quận Ba Đình",
            shipping_fee=Decimal("20000"),
            is_active=True,
        )
        self.db.add(self.area)

        # 3. Dish
        self.dish = Dish(
            id=1,
            name="Phở Bò Tái Lăn",
            price=Decimal("60000"),
            is_available=True,
            is_active=True,
            status="AVAILABLE",
        )
        self.db.add(self.dish)

        # 4. Order
        self.order = Order(
            id=1,
            order_code="ORD-TEST-001",
            user_id=1,
            recipient_name="Khách Hàng A",
            recipient_phone="0901234567",
            delivery_address="12 Liễu Giai",
            delivery_area_id=1,
            shipping_fee=Decimal("20000"),
            subtotal=Decimal("60000"),
            total_amount=Decimal("80000"),
            payment_method="COD",
            status="COMPLETED",
        )
        self.db.add(self.order)
        self.db.commit()

    # ────────────────────────────────────────────────────────────
    # 1. KIỂM THỬ MODEL & SCHEMA VOUCHER
    # ────────────────────────────────────────────────────────────
    def test_voucher_model_and_schema(self):
        # Kiểm tra Schema VoucherCreate
        schema_in = VoucherCreate(
            code="giam25k",  # gửi chữ thường -> tự động uppercase
            description="Giảm 25% tối đa 50k",
            discount_type=VoucherDiscountType.PERCENT,
            discount_value=Decimal("25"),
            min_order_amount=Decimal("100000"),
            max_discount_amount=Decimal("50000"),
            max_uses=100,
            valid_from=datetime.now(),
            valid_to=datetime.now() + timedelta(days=7),
        )
        self.assertEqual(schema_in.code, "GIAM25K")

        # Lưu vào Model Voucher trong Database
        voucher = Voucher(
            code=schema_in.code,
            description=schema_in.description,
            discount_type=schema_in.discount_type.value,
            discount_value=schema_in.discount_value,
            min_order_amount=schema_in.min_order_amount,
            max_discount_amount=schema_in.max_discount_amount,
            max_uses=schema_in.max_uses,
            used_count=0,
            valid_from=schema_in.valid_from,
            valid_to=schema_in.valid_to,
            status="ACTIVE",
        )
        self.db.add(voucher)
        self.db.commit()
        self.db.refresh(voucher)

        # Kiểm tra các trường đã được lưu đầy đủ vào Database
        self.assertIsNotNone(voucher.id)
        self.assertEqual(voucher.code, "GIAM25K")
        self.assertEqual(voucher.discount_type, "PERCENT")
        self.assertEqual(voucher.discount_value, Decimal("25"))
        self.assertEqual(voucher.min_order_amount, Decimal("100000"))
        self.assertEqual(voucher.max_discount_amount, Decimal("50000"))
        self.assertEqual(voucher.max_uses, 100)
        self.assertEqual(voucher.used_count, 0)
        self.assertEqual(voucher.status, "ACTIVE")

        # Kiểm tra Schema VoucherResponse serialize từ ORM model
        voucher_res = VoucherResponse.model_validate(voucher)
        self.assertEqual(voucher_res.code, "GIAM25K")
        self.assertEqual(voucher_res.max_discount_amount, Decimal("50000"))

    def test_voucher_schema_validation(self):
        # Chặn % > 100
        with self.assertRaises(ValueError):
            VoucherCreate(
                code="BADVOUCHER",
                discount_type=VoucherDiscountType.PERCENT,
                discount_value=Decimal("150"),
            )

        # Chặn ngày kết thúc trước ngày bắt đầu
        now = datetime.now()
        with self.assertRaises(ValueError):
            VoucherCreate(
                code="BADDATE",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=Decimal("10000"),
                valid_from=now,
                valid_to=now - timedelta(days=1),
            )

    # ────────────────────────────────────────────────────────────
    # 2. KIỂM THỬ MODEL & SCHEMA REVIEW
    # ────────────────────────────────────────────────────────────
    def test_review_model_and_schema(self):
        # Kiểm tra Schema ReviewCreate
        review_in = ReviewCreate(
            order_id=1,
            dish_id=1,
            rating=5,
            content="Phở rất thơm ngon, thịt bò mềm và nước dùng đậm đà!",
            image_url="https://example.com/images/review1.jpg",
        )
        self.assertEqual(review_in.rating, 5)

        # Lưu Model Review vào Database
        review = Review(
            order_id=review_in.order_id,
            dish_id=review_in.dish_id,
            user_id=self.customer.id,
            rating=review_in.rating,
            content=review_in.content,
            image_url=review_in.image_url,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)

        # Kiểm tra các trường và Relationships
        self.assertIsNotNone(review.id)
        self.assertEqual(review.order_id, 1)
        self.assertEqual(review.dish_id, 1)
        self.assertEqual(review.user_id, self.customer.id)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.order.order_code, "ORD-TEST-001")
        self.assertEqual(review.dish.name, "Phở Bò Tái Lăn")
        self.assertEqual(review.user.full_name, "Khách Hàng A")

        # Kiểm tra Cửa hàng phản hồi (shop_reply)
        reply_in = ReviewReplyRequest(shop_reply="Cảm ơn bạn đã ủng hộ quán ạ, chúc bạn ngon miệng!")
        review.shop_reply = reply_in.shop_reply
        review.replied_at = datetime.now()
        self.db.commit()
        self.db.refresh(review)

        self.assertIn("Cảm ơn bạn", review.shop_reply)
        self.assertIsNotNone(review.replied_at)

        # Kiểm tra Schema ReviewResponse
        review_res = ReviewResponse.model_validate(review)
        self.assertEqual(review_res.id, review.id)
        self.assertEqual(review_res.shop_reply, reply_in.shop_reply)

    def test_review_rating_validation(self):
        # Chặn rating ngoài khoảng 1-5
        with self.assertRaises(ValueError):
            ReviewCreate(order_id=1, rating=6)
        with self.assertRaises(ValueError):
            ReviewCreate(order_id=1, rating=0)

    # ────────────────────────────────────────────────────────────
    # 3. KIỂM THỬ MODEL & SCHEMA CHAT_MESSAGE
    # ────────────────────────────────────────────────────────────
    def test_chat_message_model_and_schema(self):
        # Tin nhắn từ khách hàng
        chat_in = ChatMessageCreate(
            customer_id=self.customer.id,
            content="Alo shop ơi, đơn hàng của em khoảng bao lâu thì tới?",
            sender_role="CUSTOMER",
        )

        msg1 = ChatMessage(
            customer_id=chat_in.customer_id,
            sender_id=self.customer.id,
            sender_role=chat_in.sender_role,
            content=chat_in.content,
            is_read=True,
        )
        self.db.add(msg1)

        # Tin nhắn phản hồi từ nhân viên
        msg2 = ChatMessage(
            customer_id=self.customer.id,
            sender_id=self.staff.id,
            sender_role="STAFF",
            content="Dạ shipper đang trên đường giao rồi ạ, dự kiến 10 phút nữa bạn nhé!",
            is_read=False,
        )
        self.db.add(msg2)
        self.db.commit()

        self.db.refresh(msg1)
        self.db.refresh(msg2)

        # Kiểm tra lưu trữ và quan hệ
        self.assertEqual(msg1.customer.full_name, "Khách Hàng A")
        self.assertEqual(msg1.sender.full_name, "Khách Hàng A")
        self.assertTrue(msg1.is_read)

        self.assertEqual(msg2.customer.full_name, "Khách Hàng A")
        self.assertEqual(msg2.sender.full_name, "Nhân Viên B")
        self.assertEqual(msg2.sender_role, "STAFF")
        self.assertFalse(msg2.is_read)

        # Đánh dấu đã đọc
        read_update = ChatMessageMarkRead(is_read=True)
        msg2.is_read = read_update.is_read
        self.db.commit()
        self.db.refresh(msg2)
        self.assertTrue(msg2.is_read)

        # Kiểm tra Schema ChatMessageResponse
        res = ChatMessageResponse.model_validate(msg2)
        self.assertEqual(res.id, msg2.id)
        self.assertEqual(res.customer_id, self.customer.id)
        self.assertEqual(res.sender_id, self.staff.id)
        self.assertTrue(res.is_read)


if __name__ == "__main__":
    unittest.main()

