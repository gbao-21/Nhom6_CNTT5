"""Script kiểm thử toàn bộ yêu cầu của task:
[Đánh giá] API đánh giá món sau khi nhận
1. Khách có đơn Hoàn thành (COMPLETED) được chấm sao, nhận xét (và ảnh) từng món một lần.
2. Chặn khách đánh giá đơn chưa hoàn thành.
3. Chặn khách đánh giá đơn của người khác.
4. Chặn khách đánh giá món không thuộc đơn hàng.
5. Chặn đánh giá 1 món 2 lần trong cùng đơn hàng (chỉ được đánh giá một lần).
6. Tính điểm trung bình của món chính xác.
7. Cửa hàng trả lời đánh giá (shop_reply, replied_at).
8. Admin ẩn đánh giá vi phạm (ẩn khỏi danh sách công khai và không tính vào điểm trung bình).
"""
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys
import unittest

# Đảm bảo import được backend app
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish
from app.models.order import Order, OrderItem
from app.models.review import Review
from app.models.user import User
from app.routers.reviews import (
    create_review,
    get_dish_reviews,
    get_order_reviews,
    hide_review,
    reply_to_review,
)
from app.schemas.review import (
    ReviewCreate,
    ReviewHideRequest,
    ReviewReplyRequest,
)


class ReviewApiTestCase(unittest.TestCase):
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
        # 1. Users
        self.user1 = User(
            id=1,
            full_name="Nguyễn Văn A",
            email="a@example.com",
            phone="0901234567",
            password_hash="pw1",
            role="CUSTOMER",
            is_active=True,
        )
        self.user2 = User(
            id=2,
            full_name="Trần Thị B",
            email="b@example.com",
            phone="0902345678",
            password_hash="pw2",
            role="CUSTOMER",
            is_active=True,
        )
        self.staff = User(
            id=3,
            full_name="Nhân Viên Quán",
            email="staff@example.com",
            phone="0903456789",
            password_hash="pw3",
            role="STAFF",
            is_active=True,
        )
        self.db.add_all([self.user1, self.user2, self.staff])

        # 2. Khu vực
        self.area = DeliveryArea(id=1, name="Quận Hà Đông", shipping_fee=Decimal("15000"), is_active=True)
        self.db.add(self.area)

        # 3. Dishes
        self.dish1 = Dish(id=1, name="Mì trộn Indomie", price=Decimal("45000"), is_available=True, is_active=True, status="AVAILABLE")
        self.dish2 = Dish(id=2, name="Cơm gà xối mỡ", price=Decimal("55000"), is_available=True, is_active=True, status="AVAILABLE")
        self.dish3 = Dish(id=3, name="Trà tắc khổng lồ", price=Decimal("20000"), is_available=True, is_active=True, status="AVAILABLE")
        self.db.add_all([self.dish1, self.dish2, self.dish3])

        # 4. Đơn hàng 1 của user 1 - Đã COMPLETED (có món 1 và món 2)
        self.order_completed = Order(
            id=1,
            order_code="ORD-COMPLETED-01",
            user_id=1,
            recipient_name="Nguyễn Văn A",
            recipient_phone="0901234567",
            delivery_address="123 Quang Trung",
            delivery_area_id=1,
            shipping_fee=Decimal("15000"),
            discount_amount=Decimal("0"),
            subtotal=Decimal("100000"),
            total_amount=Decimal("115000"),
            payment_method="COD",
            status="COMPLETED",
        )
        self.db.add(self.order_completed)
        self.db.flush()

        item1 = OrderItem(order_id=1, dish_id=1, dish_name="Mì trộn Indomie", dish_price=Decimal("45000"), quantity=1, line_total=Decimal("45000"))
        item2 = OrderItem(order_id=1, dish_id=2, dish_name="Cơm gà xối mỡ", dish_price=Decimal("55000"), quantity=1, line_total=Decimal("55000"))
        self.db.add_all([item1, item2])

        # 5. Đơn hàng 2 của user 1 - Chưa hoàn thành (PENDING)
        self.order_pending = Order(
            id=2,
            order_code="ORD-PENDING-02",
            user_id=1,
            recipient_name="Nguyễn Văn A",
            recipient_phone="0901234567",
            delivery_address="123 Quang Trung",
            delivery_area_id=1,
            shipping_fee=Decimal("15000"),
            discount_amount=Decimal("0"),
            subtotal=Decimal("45000"),
            total_amount=Decimal("60000"),
            payment_method="COD",
            status="PENDING",
        )
        self.db.add(self.order_pending)
        self.db.flush()
        item3 = OrderItem(order_id=2, dish_id=1, dish_name="Mì trộn Indomie", dish_price=Decimal("45000"), quantity=1, line_total=Decimal("45000"))
        self.db.add(item3)

        self.db.commit()

    # ────────────────────────────────────────────────────────────
    # 1. TEST ĐÁNH GIÁ MÓN HỢP LỆ VÀ CÁC ĐIỀU KIỆN CHẶN
    # ────────────────────────────────────────────────────────────
    def test_create_review_success(self):
        """Khách có đơn Hoàn thành được chấm sao, nhận xét và ảnh từng món."""
        req = ReviewCreate(
            order_id=1,
            dish_id=1,
            rating=5,
            content="Mì trộn rất ngon, xúc xích và trứng chuẩn vị!",
            image_url="https://example.com/mi_tron.jpg",
        )
        res = create_review(data=req, current_user_id=1, db=self.db)
        self.assertEqual(res.order_id, 1)
        self.assertEqual(res.dish_id, 1)
        self.assertEqual(res.rating, 5)
        self.assertEqual(res.content, req.content)
        self.assertEqual(res.image_url, req.image_url)
        self.assertFalse(res.is_hidden)

    def test_create_review_blocked_if_order_not_completed(self):
        """Chặn đánh giá khi đơn chưa Hoàn thành (PENDING)."""
        req = ReviewCreate(
            order_id=2,  # Đơn 2 đang PENDING
            dish_id=1,
            rating=5,
            content="Giao nhanh nhé quán ơi",
        )
        with self.assertRaises(HTTPException) as ctx:
            create_review(data=req, current_user_id=1, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("COMPLETED", ctx.exception.detail)

    def test_create_review_blocked_if_not_order_owner(self):
        """Chặn khách đánh giá đơn của người khác."""
        req = ReviewCreate(
            order_id=1,  # Đơn của User 1
            dish_id=1,
            rating=5,
            content="Đánh giá ké",
        )
        with self.assertRaises(HTTPException) as ctx:
            create_review(data=req, current_user_id=2, db=self.db)  # User 2 gọi
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("chính mình", ctx.exception.detail)

    def test_create_review_blocked_if_dish_not_in_order(self):
        """Chặn đánh giá món không có trong đơn hàng."""
        req = ReviewCreate(
            order_id=1,
            dish_id=3,  # Món 3 (Trà tắc) không có trong đơn 1
            rating=4,
            content="Ngon",
        )
        with self.assertRaises(HTTPException) as ctx:
            create_review(data=req, current_user_id=1, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("không nằm trong đơn hàng", ctx.exception.detail)

    def test_create_review_blocked_duplicate_dish_review(self):
        """Chặn đánh giá 1 món 2 lần trong cùng 1 đơn hàng (từng món một lần)."""
        req = ReviewCreate(
            order_id=1,
            dish_id=1,
            rating=5,
            content="Lần 1",
        )
        create_review(data=req, current_user_id=1, db=self.db)

        # Đánh giá lại món 1 trong đơn 1
        with self.assertRaises(HTTPException) as ctx:
            create_review(data=req, current_user_id=1, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Mỗi món chỉ được đánh giá 1 lần", ctx.exception.detail)

    # ────────────────────────────────────────────────────────────
    # 2. TEST ĐIỂM TRUNG BÌNH CỦA MÓN
    # ────────────────────────────────────────────────────────────
    def test_dish_average_rating_calculation(self):
        """Kiểm tra tính điểm trung bình chính xác của món."""
        # Khi chưa có đánh giá nào:
        summary_0 = get_dish_reviews(dish_id=1, db=self.db)
        self.assertEqual(summary_0.average_rating, 0.0)
        self.assertEqual(summary_0.total_reviews, 0)

        # Đánh giá 1: 5 sao (cho món 1 trong đơn 1 của user 1)
        create_review(
            data=ReviewCreate(order_id=1, dish_id=1, rating=5, content="Tuyệt vời"),
            current_user_id=1,
            db=self.db,
        )

        # Giả lập đơn khác của user 2 mua món 1 và hoàn thành
        order_user2 = Order(
            id=3,
            order_code="ORD-U2-03",
            user_id=2,
            recipient_name="B",
            recipient_phone="0902345678",
            delivery_address="456 Kim Mã",
            delivery_area_id=1,
            shipping_fee=Decimal("15000"),
            discount_amount=Decimal("0"),
            subtotal=Decimal("45000"),
            total_amount=Decimal("60000"),
            payment_method="COD",
            status="COMPLETED",
        )
        self.db.add(order_user2)
        self.db.flush()
        self.db.add(OrderItem(order_id=3, dish_id=1, dish_name="Mì trộn Indomie", dish_price=Decimal("45000"), quantity=1, line_total=Decimal("45000")))
        self.db.commit()

        # Đánh giá 2: 4 sao (cho món 1 trong đơn 3 của user 2)
        create_review(
            data=ReviewCreate(order_id=3, dish_id=1, rating=4, content="Hơi mặn một chút"),
            current_user_id=2,
            db=self.db,
        )

        # Điểm trung bình = (5 + 4) / 2 = 4.5
        summary = get_dish_reviews(dish_id=1, db=self.db)
        self.assertEqual(summary.total_reviews, 2)
        self.assertEqual(summary.average_rating, 4.5)
        self.assertEqual(len(summary.reviews), 2)

    # ────────────────────────────────────────────────────────────
    # 3. TEST CỬA HÀNG TRẢ LỜI ĐÁNH GIÁ
    # ────────────────────────────────────────────────────────────
    def test_shop_reply_review(self):
        """Cửa hàng trả lời đánh giá."""
        review = create_review(
            data=ReviewCreate(order_id=1, dish_id=1, rating=5, content="Món ăn rất ngon!"),
            current_user_id=1,
            db=self.db,
        )

        # Nhân viên phản hồi
        reply_req = ReviewReplyRequest(shop_reply="Cảm ơn quý khách đã ủng hộ quán ạ!")
        res = reply_to_review(review_id=review.id, data=reply_req, role="STAFF", db=self.db)
        self.assertEqual(res.shop_reply, reply_req.shop_reply)
        self.assertIsNotNone(res.replied_at)

        # Chặn nếu vai trò là CUSTOMER cố tình reply
        with self.assertRaises(HTTPException) as ctx:
            reply_to_review(review_id=review.id, data=reply_req, role="CUSTOMER", db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    # ────────────────────────────────────────────────────────────
    # 4. TEST ADMIN ẨN ĐÁNH GIÁ VI PHẠM
    # ────────────────────────────────────────────────────────────
    def test_admin_hide_review(self):
        """Admin ẩn đánh giá vi phạm, đánh giá bị ẩn không còn tính vào điểm trung bình."""
        # Tạo 2 review: 1 cái 5 sao, 1 cái 1 sao (vi phạm quy chuẩn)
        r1 = create_review(
            data=ReviewCreate(order_id=1, dish_id=1, rating=5, content="Tuyệt vời!"),
            current_user_id=1,
            db=self.db,
        )

        # Đơn khác của user 2 đánh giá 1 sao
        order_u2 = Order(
            id=4,
            order_code="ORD-U2-04",
            user_id=2,
            recipient_name="B",
            recipient_phone="0902345678",
            delivery_address="456 Kim Mã",
            delivery_area_id=1,
            shipping_fee=Decimal("15000"),
            discount_amount=Decimal("0"),
            subtotal=Decimal("45000"),
            total_amount=Decimal("60000"),
            payment_method="COD",
            status="COMPLETED",
        )
        self.db.add(order_u2)
        self.db.flush()
        self.db.add(OrderItem(order_id=4, dish_id=1, dish_name="Mì trộn Indomie", dish_price=Decimal("45000"), quantity=1, line_total=Decimal("45000")))
        self.db.commit()

        r2 = create_review(
            data=ReviewCreate(order_id=4, dish_id=1, rating=1, content="Từ ngữ tục tĩu vi phạm quy chuẩn..."),
            current_user_id=2,
            db=self.db,
        )

        # Trước khi ẩn: 2 review, trung bình = (5 + 1) / 2 = 3.0
        summary_before = get_dish_reviews(dish_id=1, db=self.db)
        self.assertEqual(summary_before.total_reviews, 2)
        self.assertEqual(summary_before.average_rating, 3.0)

        # Admin ẩn r2
        hide_req = ReviewHideRequest(is_hidden=True, reason="Vi phạm ngôn từ")
        hide_res = hide_review(review_id=r2.id, data=hide_req, role="ADMIN", db=self.db)
        self.assertTrue(hide_res.is_hidden)

        # Sau khi ẩn: công khai chỉ còn 1 review 5 sao, trung bình = 5.0
        summary_after = get_dish_reviews(dish_id=1, db=self.db)
        self.assertEqual(summary_after.total_reviews, 1)
        self.assertEqual(summary_after.average_rating, 5.0)
        self.assertEqual(summary_after.reviews[0].id, r1.id)

        # Người không phải Admin cố tình ẩn bị chặn 403
        with self.assertRaises(HTTPException) as ctx:
            hide_review(review_id=r1.id, data=hide_req, role="STAFF", db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()

