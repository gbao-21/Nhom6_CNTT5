"""Script tự động kiểm thử toàn bộ yêu cầu của task T3D25F6: [Giỏ hàng] API thêm, sửa, xoá giỏ.

Chạy nhanh (trong thư mục backend/):
    ../.venv/bin/python test_cart.py
"""
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.models.dish import Dish
from app.models.user import User
from app.routers.carts import (
    add_item_to_my_cart,
    clear_my_cart,
    delete_my_cart_item,
    get_my_cart,
    update_my_cart_item,
)
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartOption


def run_tests() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Khởi tạo dữ liệu mẫu (chỉ cần User và Dish, KHÔNG cần tạo sẵn option trong DB)
    db.add_all(
        [
            User(id=1, full_name="Gia Bảo", email="gb@test.com", password_hash="pw", is_active=True),
            User(id=2, full_name="Người dùng 2", email="u2@test.com", password_hash="pw", is_active=True),
            Dish(id=1, name="Mì trộn Indomie", price=45000, is_available=True, is_active=True, status="AVAILABLE"),
            Dish(id=2, name="Cơm gà (Hết)", price=55000, is_available=False, is_active=True, status="OUT_OF_STOCK"),
            Dish(id=3, name="Cháo sườn (Ẩn)", price=35000, is_available=True, is_active=False, status="HIDDEN"),
        ]
    )
    db.commit()

    print("1. [TEST] Thêm món vào giỏ (tùy chọn bất kỳ, không cần tạo sẵn option trong DB)...")
    line1 = add_item_to_my_cart(
        CartItemCreate(
            dish_id=1,
            selected_options=[CartOption(option_id=2), CartOption(option_id=1)],
            note="ít cay",
            quantity=2,
        ),
        current_user_id=1,
        db=db,
    )
    assert line1.quantity == 2
    print(f"   -> OK: Tạo dòng id={line1.id}, quantity={line1.quantity}")

    print("2. [TEST] Trùng hoàn toàn (không phân biệt hoa/thường ở ghi chú: 'Thêm trứng' == 'thêm trứng') -> Cộng dồn...")
    line1_dup = add_item_to_my_cart(
        CartItemCreate(
            dish_id=1,
            selected_options=[CartOption(option_id=1), CartOption(option_id=2)],
            note="  ÍT CAY  ",
            quantity=3,
        ),
        current_user_id=1,
        db=db,
    )
    assert line1_dup.id == line1.id and line1_dup.quantity == 5
    print(f"   -> OK: Cộng dồn vào dòng id={line1_dup.id}, quantity={line1_dup.quantity}")

    print("3. [TEST] Cùng món nhưng khác ghi chú / khác tùy chọn -> Tạo dòng riêng...")
    line2 = add_item_to_my_cart(
        CartItemCreate(
            dish_id=1,
            selected_options=[CartOption(option_id=1), CartOption(option_id=2)],
            note="nhiều hành",
            quantity=1,
        ),
        current_user_id=1,
        db=db,
    )
    line3 = add_item_to_my_cart(
        CartItemCreate(
            dish_id=1,
            selected_options=[CartOption(option_id=99)],
            note="ít cay",
            quantity=1,
        ),
        current_user_id=1,
        db=db,
    )
    assert line2.id != line1.id and line3.id != line1.id
    print(f"   -> OK: Tạo dòng riêng id={line2.id} (khác ghi chú) và id={line3.id} (khác tùy chọn)")

    print("4. [TEST] Chặn món hết hàng và món bị ẩn...")
    for desc, payload in [
        ("Món hết hàng", CartItemCreate(dish_id=2, quantity=1)),
        ("Món bị ẩn", CartItemCreate(dish_id=3, quantity=1)),
    ]:
        try:
            add_item_to_my_cart(payload, current_user_id=1, db=db)
            raise AssertionError(f"Lỗi: Không chặn được {desc}")
        except HTTPException as exc:
            assert exc.status_code == 400
            print(f"   -> OK ({desc}): Chặn thành công với lỗi 400 - {exc.detail}")

    print("5. [TEST] Chỉ thao tác trên giỏ của mình (User 2 cố sửa/xoá giỏ User 1)...")
    try:
        update_my_cart_item(line1.id, CartItemUpdate(quantity=99), current_user_id=2, db=db)
        raise AssertionError("Lỗi: User 2 sửa được giỏ của User 1")
    except HTTPException as exc:
        assert exc.status_code == 403
        print(f"   -> OK (Chặn sửa giỏ người khác): 403 - {exc.detail}")

    try:
        delete_my_cart_item(line1.id, current_user_id=2, db=db)
        raise AssertionError("Lỗi: User 2 xoá được giỏ của User 1")
    except HTTPException as exc:
        assert exc.status_code == 403
        print(f"   -> OK (Chặn xoá giỏ người khác): 403 - {exc.detail}")

    print("6. [TEST] Sửa giỏ hàng (nếu sửa xong trùng dòng khác thì tự gộp cộng dồn)...")
    merged = update_my_cart_item(
        line2.id,
        CartItemUpdate(note="ít cay"),
        current_user_id=1,
        db=db,
    )
    assert merged.id == line1.id and merged.quantity == 6
    print(f"   -> OK: Gộp dòng id={line2.id} vào id={line1.id}, quantity mới={merged.quantity}")

    print("7. [TEST] Xoá dòng trong giỏ và xoá toàn bộ giỏ...")
    delete_my_cart_item(line3.id, current_user_id=1, db=db)
    assert len(get_my_cart(current_user_id=1, db=db).items) == 1
    clear_my_cart(current_user_id=1, db=db)
    assert len(get_my_cart(current_user_id=1, db=db).items) == 0
    print("   -> OK: Xoá 1 dòng và xoá sạch giỏ thành công!")
    print("\n✅ TẤT CẢ CÁC BÀI TEST CHO TASK T3D25F6 ĐỀU VƯỢT QUA!")


if __name__ == "__main__":
    run_tests()
