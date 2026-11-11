"""Unit tests cho 3 task:
1. [Database] Model OrderStatusHistory và bảng chuyển trạng thái hợp lệ.
2. [Đơn hàng] API đơn của tôi và theo dõi đơn (kèm món, tuỳ chọn, dòng thời gian).
3. [Đơn hàng] API huỷ đơn theo điều kiện (khách huỷ khi PENDING, nhân viên huỷ trước DELIVERING kèm lý do).
"""
import unittest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.order_status import (
    VALID_STATUS_TRANSITIONS,
    is_valid_status_transition,
)
from app.db.base import Base
from app.dependencies import get_db
from app.main import app
from app.models.category import Category
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish, DishOption
from app.models.order import Order, OrderItem, OrderStatusHistory
from app.models.user import User


class OrderStatusAndCancellationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Dùng SQLite in-memory cho test độc lập và tốc độ cao
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
        )

    def setUp(self):
        Base.metadata.create_all(bind=self.engine)
        self.db = self.TestingSessionLocal()

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Seed dữ liệu mẫu
        self.seed_data()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        app.dependency_overrides.clear()

    def seed_data(self):
        # 1. Users
        self.user_customer1 = User(
            id=1,
            full_name="Khách Hàng 1",
            email="customer1@example.com",
            phone="0911111111",
            password_hash="hash1",
            role="CUSTOMER",
        )
        self.user_customer2 = User(
            id=2,
            full_name="Khách Hàng 2",
            email="customer2@example.com",
            phone="0922222222",
            password_hash="hash2",
            role="CUSTOMER",
        )
        self.user_staff = User(
            id=3,
            full_name="Nhân Viên 1",
            email="staff1@example.com",
            phone="0933333333",
            password_hash="hash3",
            role="STAFF",
        )
        self.db.add_all([self.user_customer1, self.user_customer2, self.user_staff])

        # 2. Category & Dish
        self.cat = Category(id=1, name="Món Nước", description="Các món nước đêm")
        self.db.add(self.cat)
        self.db.flush()

        self.dish = Dish(
            id=1,
            category_id=self.cat.id,
            name="Phở Bò Tái Nạm",
            description="Phở thơm ngon",
            price=Decimal("50000.00"),
            is_available=True,
        )
        self.db.add(self.dish)
        self.db.flush()

        self.dish_option = DishOption(
            id=1,
            dish_id=self.dish.id,
            name="Thêm quẩy giòn",
            price=Decimal("5000.00"),
            is_available=True,
        )
        self.db.add(self.dish_option)

        # 3. Delivery Area
        self.area = DeliveryArea(
            id=1,
            name="Cầu Giấy",
            shipping_fee=Decimal("15000.00"),
            is_active=True,
        )
        self.db.add(self.area)
        self.db.commit()

    def create_sample_order(self, user_id=1):
        order_payload = {
            "recipient_name": "Nguyễn Văn A",
            "recipient_phone": "0987654321",
            "delivery_address": "123 Cầu Giấy, Hà Nội",
            "delivery_area_id": 1,
            "payment_method": "COD",
            "items": [
                {
                    "dish_id": 1,
                    "selected_options": [{"option_id": 1}],
                    "note": "Ít hành",
                    "quantity": 2,
                }
            ],
        }
        res = self.client.post(f"/api/orders?user_id={user_id}", json=order_payload)
        self.assertEqual(res.status_code, 201)
        return res.json()

    # ==========================
    # TASK 1: Model OrderStatusHistory & Luồng / Bảng trạng thái hợp lệ
    # ==========================
    def test_task1_model_and_initial_history(self):
        order_data = self.create_sample_order(user_id=1)
        order_id = order_data["id"]

        histories = (
            self.db.query(OrderStatusHistory)
            .filter_by(order_id=order_id)
            .order_by(OrderStatusHistory.created_at.asc())
            .all()
        )
        self.assertEqual(len(histories), 1)
        self.assertIsNone(histories[0].old_status)
        self.assertEqual(histories[0].new_status, "PENDING")
        self.assertEqual(histories[0].changed_by, 1)

    def test_task1_valid_transition_table(self):
        # Kiểm tra bảng chuyển trạng thái hợp lệ
        self.assertTrue(is_valid_status_transition("PENDING", "CONFIRMED"))
        self.assertTrue(is_valid_status_transition("CONFIRMED", "PREPARING"))
        self.assertTrue(is_valid_status_transition("PREPARING", "DELIVERING"))
        self.assertTrue(is_valid_status_transition("DELIVERING", "COMPLETED"))

        # Huỷ hợp lệ
        self.assertTrue(is_valid_status_transition("PENDING", "CANCELLED"))
        self.assertTrue(is_valid_status_transition("CONFIRMED", "CANCELLED"))
        self.assertTrue(is_valid_status_transition("PREPARING", "CANCELLED"))

        # Chuyển trạng thái bất hợp lệ
        self.assertFalse(is_valid_status_transition("PENDING", "DELIVERING"))
        self.assertFalse(is_valid_status_transition("DELIVERING", "CANCELLED"))
        self.assertFalse(is_valid_status_transition("COMPLETED", "CANCELLED"))
        self.assertFalse(is_valid_status_transition("CANCELLED", "CONFIRMED"))

    def test_task1_update_status_flow(self):
        order_data = self.create_sample_order(user_id=1)
        order_id = order_data["id"]

        # PENDING -> CONFIRMED
        res = self.client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "CONFIRMED", "note": "Nhân viên xác nhận"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "CONFIRMED")

        # CONFIRMED -> PREPARING
        res = self.client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "PREPARING", "note": "Bếp bắt đầu nấu"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "PREPARING")

        # Thử nhảy cóc: PREPARING -> COMPLETED (Sai luồng, phải qua DELIVERING)
        res = self.client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "COMPLETED"},
        )
        self.assertEqual(res.status_code, 400)

        # PREPARING -> DELIVERING
        res = self.client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "DELIVERING", "note": "Shipper nhận hàng"},
        )
        self.assertEqual(res.status_code, 200)

        # DELIVERING -> COMPLETED
        res = self.client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "COMPLETED", "note": "Giao thành công"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "COMPLETED")

        # Kiểm tra timeline lịch sử đầy đủ
        order_detail = self.client.get(f"/api/orders/{order_id}").json()
        timeline = order_detail["status_history"]
        self.assertEqual(len(timeline), 5)
        self.assertEqual(timeline[0]["new_status"], "PENDING")
        self.assertEqual(timeline[1]["new_status"], "CONFIRMED")
        self.assertEqual(timeline[2]["new_status"], "PREPARING")
        self.assertEqual(timeline[3]["new_status"], "DELIVERING")
        self.assertEqual(timeline[4]["new_status"], "COMPLETED")

    # ==========================
    # TASK 2: API Đơn của tôi và Theo dõi đơn
    # ==========================
    def test_task2_my_orders_and_isolation(self):
        # User 1 tạo 2 đơn
        self.create_sample_order(user_id=1)
        self.create_sample_order(user_id=1)

        # User 2 tạo 1 đơn
        self.create_sample_order(user_id=2)

        # Khách 1 xem danh sách đơn của mình
        res1 = self.client.get("/api/orders/my-orders?user_id=1")
        self.assertEqual(res1.status_code, 200)
        orders1 = res1.json()
        self.assertEqual(len(orders1), 2)
        for ord in orders1:
            self.assertEqual(ord["user_id"], 1)

        # Khách 2 chỉ xem được đơn của mình
        res2 = self.client.get("/api/orders/my-orders?user_id=2")
        self.assertEqual(res2.status_code, 200)
        orders2 = res2.json()
        self.assertEqual(len(orders2), 1)
        self.assertEqual(orders2[0]["user_id"], 2)

    def test_task2_filter_my_orders_by_status(self):
        ord1 = self.create_sample_order(user_id=1)
        ord2 = self.create_sample_order(user_id=1)

        # Chuyển ord1 sang CONFIRMED
        self.client.patch(
            f"/api/orders/{ord1['id']}/status",
            json={"status": "CONFIRMED"},
        )

        # Lọc trạng thái PENDING
        res_pending = self.client.get("/api/orders/my-orders?user_id=1&status=PENDING")
        self.assertEqual(res_pending.status_code, 200)
        items = res_pending.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], ord2["id"])

        # Lọc trạng thái CONFIRMED
        res_confirmed = self.client.get("/api/orders/my-orders?user_id=1&status=CONFIRMED")
        self.assertEqual(res_confirmed.status_code, 200)
        items_c = res_confirmed.json()
        self.assertEqual(len(items_c), 1)
        self.assertEqual(items_c[0]["id"], ord1["id"])

    def test_task2_track_order_detail(self):
        ord_data = self.create_sample_order(user_id=1)
        order_id = ord_data["id"]

        # Xem chi tiết đơn kèm món, tuỳ chọn, dòng thời gian
        res = self.client.get(f"/api/orders/my-orders/{order_id}?user_id=1")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Kiểm tra chi tiết món & tuỳ chọn
        self.assertEqual(len(data["items"]), 1)
        item = data["items"][0]
        self.assertEqual(item["dish_name"], "Phở Bò Tái Nạm")
        self.assertEqual(len(item["selected_options"]), 1)
        self.assertEqual(item["selected_options"][0]["name"], "Thêm quẩy giòn")

        # Kiểm tra dòng thời gian
        self.assertTrue(len(data["status_history"]) >= 1)
        self.assertEqual(data["status_history"][0]["new_status"], "PENDING")

        # Khách 2 không được xem đơn của khách 1
        res_forbidden = self.client.get(f"/api/orders/my-orders/{order_id}?user_id=2")
        self.assertEqual(res_forbidden.status_code, 403)

    # ==========================
    # TASK 3: API Huỷ đơn theo điều kiện
    # ==========================
    def test_task3_customer_cancel_success_when_pending(self):
        ord_data = self.create_sample_order(user_id=1)
        order_id = ord_data["id"]

        # Khách huỷ khi còn Chờ xác nhận
        res = self.client.post(
            f"/api/orders/{order_id}/cancel",
            json={"reason": "Tôi đặt nhầm món, muốn huỷ đặt lại", "user_id": 1},
        )
        self.assertEqual(res.status_code, 200)
        res_json = res.json()
        self.assertEqual(res_json["status"], "CANCELLED")

        # Kiểm tra lịch sử trạng thái
        last_history = res_json["status_history"][-1]
        self.assertEqual(last_history["old_status"], "PENDING")
        self.assertEqual(last_history["new_status"], "CANCELLED")
        self.assertEqual(last_history["changed_by"], 1)
        self.assertIn("đặt nhầm món", last_history["note"])

    def test_task3_customer_cannot_cancel_other_user_order(self):
        ord_data = self.create_sample_order(user_id=1)
        order_id = ord_data["id"]

        # Khách 2 cố huỷ đơn của khách 1 -> 403
        res = self.client.post(
            f"/api/orders/{order_id}/cancel",
            json={"reason": "Huỷ trộm", "user_id": 2},
        )
        self.assertEqual(res.status_code, 403)

    def test_task3_customer_cannot_cancel_after_confirmed(self):
        ord_data = self.create_sample_order(user_id=1)
        order_id = ord_data["id"]

        # Đơn đã xác nhận
        self.client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "CONFIRMED"},
        )

        # Khách cố huỷ khi đã CONFIRMED -> 400
        res = self.client.post(
            f"/api/orders/{order_id}/cancel",
            json={"reason": "Không muốn mua nữa", "user_id": 1},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Chờ xác nhận", res.json()["detail"])

    def test_task3_staff_cancel_before_delivering_with_reason(self):
        ord_data = self.create_sample_order(user_id=1)
        order_id = ord_data["id"]

        # Đơn chuyển sang PREPARING (bếp chuẩn bị)
        self.client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "CONFIRMED"},
        )
        self.client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "PREPARING"},
        )

        # Nhân viên huỷ đơn trước Đang giao kèm lý do "Hết quẩy và phở"
        res = self.client.post(
            f"/api/orders/{order_id}/cancel",
            json={"reason": "Hết món", "user_id": 3},  # user 3 có role STAFF
        )
        self.assertEqual(res.status_code, 200)
        res_json = res.json()
        self.assertEqual(res_json["status"], "CANCELLED")

        # Kiểm tra lịch sử
        last_history = res_json["status_history"][-1]
        self.assertEqual(last_history["old_status"], "PREPARING")
        self.assertEqual(last_history["new_status"], "CANCELLED")
        self.assertEqual(last_history["changed_by"], 3)
        self.assertIn("Hết món", last_history["note"])

    def test_task3_staff_cancel_without_reason_rejected(self):
        ord_data = self.create_sample_order(user_id=1)
        order_id = ord_data["id"]

        # Nhân viên cố huỷ nhưng để lý do trống
        res = self.client.post(
            f"/api/orders/{order_id}/cancel",
            json={"reason": "   ", "user_id": 3},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("lý do", res.json()["detail"])

    def test_task3_staff_cannot_cancel_when_delivering(self):
        ord_data = self.create_sample_order(user_id=1)
        order_id = ord_data["id"]

        # Chuyển đến DELIVERING
        self.client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"})
        self.client.patch(f"/api/orders/{order_id}/status", json={"status": "PREPARING"})
        self.client.patch(f"/api/orders/{order_id}/status", json={"status": "DELIVERING"})

        # Nhân viên cố huỷ khi đang giao -> 400
        res = self.client.post(
            f"/api/orders/{order_id}/cancel",
            json={"reason": "Muốn huỷ khi đang giao", "user_id": 3},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("trước khi Đang giao", res.json()["detail"])


if __name__ == "__main__":
    unittest.main()
