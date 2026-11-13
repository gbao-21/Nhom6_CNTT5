"""Tự động bổ sung cột còn thiếu (nếu bảng cũ) và tạo dữ liệu mẫu để test ngay trên /docs."""
from decimal import Decimal

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models.category import Category
from app.models.chat_message import ChatMessage
from app.models.coupon import Coupon
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish
from app.models.review import Review
from app.models.user import User
from app.models.voucher import Voucher


def ensure_schema_and_seed_data() -> None:
    """Đảm bảo các bảng có đủ cột còn thiếu và chèn dữ liệu mẫu nếu DB đang trống."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "dishes" in table_names:
        existing_cols = {col["name"] for col in inspector.get_columns("dishes")}
        with engine.begin() as conn:
            if "is_active" not in existing_cols:
                conn.execute(
                    text("ALTER TABLE dishes ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1")
                )
            if "status" not in existing_cols:
                conn.execute(
                    text(
                        "ALTER TABLE dishes ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'AVAILABLE'"
                    )
                )

    if "orders" in table_names:
        order_cols = {col["name"] for col in inspector.get_columns("orders")}
        with engine.begin() as conn:
            if "coupon_code" not in order_cols:
                conn.execute(
                    text("ALTER TABLE orders ADD COLUMN coupon_code VARCHAR(50) NULL AFTER shipping_fee")
                )

    db: Session = SessionLocal()
    try:
        # 1. Seed Users (User 1 và User 2 để test phân quyền giỏ hàng)
        if db.get(User, 1) is None:
            db.add(
                User(
                    id=1,
                    full_name="Thái Nguyễn Gia Bảo",
                    email="giabao@example.com",
                    phone="0901234567",
                    password_hash="hashed_pw_1",
                    role="CUSTOMER",
                    is_active=True,
                )
            )
        if db.get(User, 2) is None:
            db.add(
                User(
                    id=2,
                    full_name="Nguyễn Văn B",
                    email="vanb@example.com",
                    phone="0902345678",
                    password_hash="hashed_pw_2",
                    role="CUSTOMER",
                    is_active=True,
                )
            )
        db.commit()

        # 2. Seed Category
        if db.get(Category, 1) is None:
            db.add(
                Category(
                    id=1,
                    name="Món chính đêm",
                    description="Các món ăn no giao đêm",
                    is_active=True,
                )
            )
            db.commit()

        # 3. Seed Dishes (1: Còn bán, 2: Hết hàng, 3: Bị ẩn)
        if db.get(Dish, 1) is None:
            db.add(
                Dish(
                    id=1,
                    category_id=1,
                    name="Mì trộn Indomie đặc biệt",
                    description="Mì trộn kèm trứng lòng đào và xúc xích",
                    price=Decimal("45000"),
                    is_available=True,
                    is_active=True,
                    status="AVAILABLE",
                )
            )
        if db.get(Dish, 2) is None:
            db.add(
                Dish(
                    id=2,
                    category_id=1,
                    name="Cơm gà xối mỡ (Hết hàng)",
                    description="Món dùng để test chặn món hết hàng",
                    price=Decimal("55000"),
                    is_available=False,
                    is_active=True,
                    status="OUT_OF_STOCK",
                )
            )
        if db.get(Dish, 3) is None:
            db.add(
                Dish(
                    id=3,
                    category_id=1,
                    name="Cháo sườn sụn (Món ẩn)",
                    description="Món dùng để test chặn món bị ẩn",
                    price=Decimal("35000"),
                    is_available=True,
                    is_active=False,
                    status="HIDDEN",
                )
            )

        # 4. Seed DeliveryArea
        if db.get(DeliveryArea, 1) is None:
            db.add(
                DeliveryArea(
                    id=1,
                    name="Quận Hà Đông",
                    shipping_fee=Decimal("15000"),
                    is_active=True,
                )
            )

        # 5. Seed Coupons
        if db.query(Coupon).filter(Coupon.code == "GIAM10K").first() is None:
            db.add(
                Coupon(
                    code="GIAM10K",
                    description="Giảm 10.000đ cho đơn từ 40.000đ",
                    discount_type="FIXED",
                    discount_value=Decimal("10000"),
                    min_order_amount=Decimal("40000"),
                    max_uses=10,
                    used_count=0,
                    status="ACTIVE",
                )
            )
        if db.query(Coupon).filter(Coupon.code == "SALE10").first() is None:
            db.add(
                Coupon(
                    code="SALE10",
                    description="Giảm 10% cho mọi đơn hàng",
                    discount_type="PERCENT",
                    discount_value=Decimal("10"),
                    min_order_amount=Decimal("0"),
                    max_uses=50,
                    used_count=0,
                    status="ACTIVE",
                )
            )

        # 6. Seed Vouchers
        if db.query(Voucher).filter(Voucher.code == "VOUCHER20").first() is None:
            db.add(
                Voucher(
                    code="VOUCHER20",
                    description="Giảm 20% tối đa 30.000đ cho đơn từ 50.000đ",
                    discount_type="PERCENT",
                    discount_value=Decimal("20"),
                    min_order_amount=Decimal("50000"),
                    max_discount_amount=Decimal("30000"),
                    max_uses=100,
                    used_count=0,
                    status="ACTIVE",
                )
            )

        # 7. Seed ChatMessage
        if db.query(ChatMessage).first() is None:
            db.add(
                ChatMessage(
                    customer_id=1,
                    sender_id=1,
                    sender_role="CUSTOMER",
                    content="Shop ơi quán còn mở cửa đến mấy giờ ạ?",
                    is_read=True,
                )
            )
            db.add(
                ChatMessage(
                    customer_id=1,
                    sender_id=2,
                    sender_role="STAFF",
                    content="Chào bạn, quán mở cửa giao đêm đến 3h sáng bạn nhé!",
                    is_read=False,
                )
            )
        db.commit()
    finally:
        db.close()
