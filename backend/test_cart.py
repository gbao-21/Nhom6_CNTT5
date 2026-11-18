"""Script tự động kiểm thử toàn bộ yêu cầu của Giỏ hàng:
- Thêm, sửa, xoá giỏ hàng (cộng dồn khi trùng hoàn toàn, tách dòng khi khác tùy chọn/ghi chú, chặn món hết/ẩn, chỉ thao tác trên giỏ của mình)
- Xem giỏ và tính tiền ở server (thành tiền từng dòng, tạm tính, phí ship theo khu vực, giảm giá, tổng, báo khi món đã hết hoặc đổi giá)

Chạy nhanh (trong thư mục backend/):
    ../.venv/bin/python test_cart.py
"""
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish
from app.models.user import User
from app.routers.carts import (
    add_item_to_my_cart,
    calculate_my_cart,
    clear_my_cart,
    delete_my_cart_item,
    get_my_cart,
    update_my_cart_item,
)
from app.schemas.cart import (
    CartCalculateRequest,
    CartItemCreate,
    CartItemUpdate,
    CartOption,
)


def run_tests() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Khởi tạo dữ liệu mẫu
    dish_1 = Dish(
        id=1,
        name="Mì trộn Indomie",
        price=Decimal("45000"),
        is_available=True,
        is_active=True,
        status="AVAILABLE",
    )
    dish_2 = Dish(
        id=2,
        name="Cơm gà (Hết)",
        price=Decimal("55000"),
        is_available=False,
        is_active=True,
        status="OUT_OF_STOCK",
    )
    dish_3 = Dish(
        id=3,
        name="Cháo sườn (Ẩn)",
        price=Decimal("35000"),
        is_available=True,
        is_active=False,
        status="HIDDEN",
    )
    area_1 = DeliveryArea(id=1, name="Quận Hà Đông", shipping_fee=Decimal("15000"), is_active=True)

    db.add_all(
        [
            User(id=1, full_name="Gia Bảo", email="gb@test.com", password_hash="pw", is_active=True),
            User(id=2, full_name="Người dùng 2", email="u2@test.com", password_hash="pw", is_active=True),
            dish_1,
            dish_2,
            dish_3,
            area_1,
        ]
    )
    db.commit()

    print("1. [TEST] Thêm món vào giỏ kèm tùy chọn có giá (tính thành tiền từng dòng)...")
    line1 = add_item_to_my_cart(
        CartItemCreate(
            dish_id=1,
            selected_options=[
                CartOption(option_id=2, name="Phô mai", price=10000),
                CartOption(option_id=1, name="Trứng lòng đào", price=7000),
            ],
            note="ít cay",
            quantity=2,
        ),
        current_user_id=1,
        db=db,
    )
    # Đơn giá 1 phần = 45,000 + (7,000 + 10,000) = 62,000 -> 2 phần = 124,000
    assert line1.quantity == 2
    assert line1.unit_price == 62000.0
    assert line1.line_total == 124000.0
    print(f"   -> OK: Tạo dòng id={line1.id}, unit_price={line1.unit_price:,.0f}đ, line_total={line1.line_total:,.0f}đ")

    print("2. [TEST] Trùng hoàn toàn (không phân biệt hoa/thường: 'ÍT CAY' == 'ít cay') -> Cộng dồn...")
    line1_dup = add_item_to_my_cart(
        CartItemCreate(
            dish_id=1,
            selected_options=[
                CartOption(option_id=1, name="Trứng lòng đào", price=7000),
                CartOption(option_id=2, name="Phô mai", price=10000),
            ],
            note="  ÍT CAY  ",
            quantity=1,
        ),
        current_user_id=1,
        db=db,
    )
    assert line1_dup.id == line1.id and line1_dup.quantity == 3
    assert line1_dup.line_total == 186000.0
    print(f"   -> OK: Cộng dồn vào dòng id={line1_dup.id}, quantity={line1_dup.quantity}, line_total={line1_dup.line_total:,.0f}đ")

    print("3. [TEST] Xem giỏ & tính tiền ở server (tạm tính + phí ship khu vực + giảm giá = tổng)...")
    cart_calc = calculate_my_cart(
        CartCalculateRequest(delivery_area_id=1, voucher_code="GIAM10"),
        current_user_id=1,
        db=db,
    )
    # Tạm tính = 186,000 | Phí ship (khu vực 1) = 15,000 | Giảm giá 10% = 18,600 | Tổng = 182,400
    assert cart_calc.subtotal == 186000.0
    assert cart_calc.shipping_fee == 15000.0
    assert cart_calc.discount_amount == 18600.0
    assert cart_calc.total_amount == 182400.0
    print(
        f"   -> OK: Tạm tính={cart_calc.subtotal:,.0f}đ, Ship={cart_calc.shipping_fee:,.0f}đ, "
        f"Giảm giá={cart_calc.discount_amount:,.0f}đ => Tổng={cart_calc.total_amount:,.0f}đ"
    )

    print("4. [TEST] Báo khi món ăn bị ĐỔI GIÁ ở server...")
    dish_1.price = Decimal("50000")  # Đổi giá món 1 từ 45,000đ -> 50,000đ
    db.commit()

    cart_after_price_change = get_my_cart(
        delivery_area_id=1,
        voucher_code=None,
        current_user_id=1,
        db=db,
    )
    assert cart_after_price_change.has_price_changes is True
    assert cart_after_price_change.items[0].old_price == 45000.0
    assert cart_after_price_change.items[0].dish_price == 50000.0
    # Giá mới 1 phần = 50,000 + 17,000 = 67,000 -> 3 phần = 201,000
    assert cart_after_price_change.subtotal == 201000.0
    print(f"   -> OK: Phát hiện đổi giá! Cảnh báo: {cart_after_price_change.warnings}")

    print("5. [TEST] Báo khi món trong giỏ bị HẾT HÀNG ở server...")
    dish_1.is_available = False
    dish_1.status = "OUT_OF_STOCK"
    db.commit()

    cart_after_sold_out = get_my_cart(
        delivery_area_id=1,
        voucher_code=None,
        current_user_id=1,
        db=db,
    )
    assert cart_after_sold_out.has_unavailable_items is True
    assert cart_after_sold_out.can_checkout is False
    print(f"   -> OK: Phát hiện món hết hàng! Cảnh báo: {cart_after_sold_out.warnings}")

    # Khôi phục món 1 về trạng thái còn hàng để test tiếp xoá giỏ
    dish_1.is_available = True
    dish_1.status = "AVAILABLE"
    db.commit()

    print("6. [TEST] Chỉ thao tác trên giỏ của mình & Xoá giỏ...")
    try:
        delete_my_cart_item(line1.id, current_user_id=2, db=db)
        raise AssertionError("Lỗi: User 2 xoá được giỏ của User 1")
    except HTTPException as exc:
        assert exc.status_code == 403
        print(f"   -> OK (Chặn User 2): 403 - {exc.detail}")

    clear_my_cart(current_user_id=1, db=db)
    assert len(get_my_cart(None, None, current_user_id=1, db=db).items) == 0
    print("   -> OK: Xoá sạch giỏ thành công!")
    print("\n✅ TẤT CẢ CÁC BÀI TEST XEM GIỎ & TÍNH TIỀN ĐỀU VƯỢT QUA!")


if __name__ == "__main__":
    run_tests()
