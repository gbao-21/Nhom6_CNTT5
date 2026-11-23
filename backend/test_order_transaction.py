"""Script kiểm thử tự động task: [Đặt món] API đặt món trong transaction.

Chạy nhanh (trong thư mục backend/):
    ../.venv/bin/python test_order_transaction.py
"""
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.models.cart import Cart, CartItem
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish
from app.models.order import Order
from app.models.user import User
from app.routers.orders import create_order
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
    OrderOptionCreate,
    PaymentMethod,
)


def run_tests() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(id=1, full_name="Gia Bảo", email="gb@test.com", password_hash="pw", is_active=True)
    area = DeliveryArea(id=1, name="Quận Hà Đông", shipping_fee=Decimal("15000"), is_active=True)
    dish_ok = Dish(
        id=1,
        name="Mì trộn Indomie đặc biệt",
        price=Decimal("45000"),
        is_available=True,
        is_active=True,
        status="AVAILABLE",
    )
    dish_sold_out = Dish(
        id=2,
        name="Cơm gà xối mỡ (Hết hàng)",
        price=Decimal("55000"),
        is_available=False,
        is_active=True,
        status="OUT_OF_STOCK",
    )
    cart = Cart(id=1, user_id=1)
    cart_item = CartItem(
        cart_id=1,
        dish_id=1,
        selected_options=[{"option_id": 1, "name": "Thêm trứng", "price": 7000}],
        note="ít cay",
        quantity=2,
    )
    db.add_all([user, area, dish_ok, dish_sold_out, cart, cart_item])
    db.commit()

    print("1. [TEST] Chặn giờ giao mong muốn nằm ngoài giờ mở cửa (03:00 sáng)...")
    try:
        create_order(
            data=OrderCreate(
                recipient_name="Gia Bảo",
                recipient_phone="0901234567",
                delivery_address="123 Nguyễn Trãi, Hà Đông",
                delivery_area_id=1,
                payment_method=PaymentMethod.COD,
                desired_delivery_at=datetime(2026, 11, 16, 3, 0),
            ),
            current_user_id=1,
            x_idempotency_key=None,
            db=db,
        )
        raise AssertionError("Lỗi: Không chặn giờ giao ngoài giờ mở cửa")
    except HTTPException as exc:
        assert exc.status_code == 400
        # Giỏ hàng vẫn còn nguyên vì đã rollback
        assert len(db.get(Cart, 1).items) == 1
        print(f"   -> OK: Chặn thành công (400) & giữ nguyên giỏ hàng - {exc.detail}")

    print("2. [TEST] Chặn đặt món đã hết hàng & Rollback transaction (giỏ hàng không bị xoá)...")
    try:
        create_order(
            data=OrderCreate(
                recipient_name="Gia Bảo",
                recipient_phone="0901234567",
                delivery_address="123 Nguyễn Trãi, Hà Đông",
                delivery_area_id=1,
                payment_method=PaymentMethod.COD,
                desired_delivery_at=datetime(2026, 11, 16, 19, 30),
                items=[
                    OrderItemCreate(dish_id=1, quantity=1),
                    OrderItemCreate(dish_id=2, quantity=1),  # Món số 2 đã hết hàng
                ],
            ),
            current_user_id=1,
            x_idempotency_key=None,
            db=db,
        )
        raise AssertionError("Lỗi: Không chặn món hết hàng")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert len(list(db.scalars(select(Order)))) == 0
        assert len(db.get(Cart, 1).items) == 1
        print(f"   -> OK: Rollback thành công, không tạo đơn lỗi & giỏ hàng còn nguyên - {exc.detail}")

    print("3. [TEST] Đặt món thành công trong 1 transaction (Lưu giá & tùy chọn lúc đặt + Tạo đơn PENDING + Xoá giỏ)...")
    order = create_order(
        data=OrderCreate(
            recipient_name="Gia Bảo",
            recipient_phone="0901234567",
            delivery_address="123 Nguyễn Trãi, Hà Đông",
            delivery_area_id=1,
            payment_method=PaymentMethod.COD,
            desired_delivery_at=datetime(2026, 11, 16, 19, 30),
            # Không cần truyền items -> tự lấy từ giỏ hàng và xoá giỏ trong cùng transaction!
        ),
        current_user_id=1,
        x_idempotency_key="KEY-ORDER-001",
        db=db,
    )
    assert order.status == "PENDING"
    assert len(order.items) == 1
    assert order.items[0].dish_name == "Mì trộn Indomie đặc biệt"
    assert order.items[0].dish_price == Decimal("45000")
    assert order.items[0].options_price == Decimal("7000")
    assert order.items[0].line_total == Decimal("104000")  # (45000 + 7000) * 2
    assert order.subtotal == Decimal("104000")
    assert order.shipping_fee == Decimal("15000")
    assert order.total_amount == Decimal("119000")
    # Giỏ hàng đã được xoá sạch trong cùng transaction
    assert len(db.get(Cart, 1).items) == 0
    print(
        f"   -> OK: Tạo đơn {order.order_code} trạng thái '{order.status}', "
        f"total={order.total_amount:,.0f}đ, giỏ hàng còn {len(db.get(Cart, 1).items)} món!"
    )

    print("4. [TEST] Đổi giá món sau khi đặt -> Giá lưu trong đơn hàng cũ KHÔNG bị thay đổi...")
    dish_ok.price = Decimal("99000")
    db.commit()
    db.refresh(order)
    assert order.items[0].dish_price == Decimal("45000")
    dish_ok.price = Decimal("45000")
    db.commit()
    print("   -> OK: Snapshot giá lúc đặt (45,000đ) được bảo toàn tuyệt đối!")

    print("5. [TEST] Chống bấm đặt 2 lần liên tiếp (Double-submit protection)...")
    try:
        create_order(
            data=OrderCreate(
                recipient_name="Gia Bảo",
                recipient_phone="0901234567",
                delivery_address="123 Nguyễn Trãi, Hà Đông",
                delivery_area_id=1,
                payment_method=PaymentMethod.COD,
                desired_delivery_at=datetime(2026, 11, 16, 19, 30),
                items=[
                    OrderItemCreate(
                        dish_id=1,
                        selected_options=[OrderOptionCreate(option_id=1, name="Thêm trứng", price=Decimal("7000"))],
                        note="ít cay",
                        quantity=2,
                    )
                ],
            ),
            current_user_id=1,
            x_idempotency_key=None,
            db=db,
        )
        raise AssertionError("Lỗi: Cho phép bấm đặt 2 lần trùng nhau liên tiếp")
    except HTTPException as exc:
        assert exc.status_code == 409
        print(f"   -> OK: Chặn bấm đặt 2 lần thành công (409 Conflict) - {exc.detail}")

    print("\n✅ TẤT CẢ CÁC BÀI TEST CHO TASK [ĐẶT MÓN TRONG TRANSACTION] ĐỀU VƯỢT QUA!")


if __name__ == "__main__":
    run_tests()

