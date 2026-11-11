"""Tự động bổ sung cột còn thiếu (nếu bảng cũ) và tạo dữ liệu mẫu để test ngay trên /docs."""
from decimal import Decimal

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models.category import Category
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish
from app.models.user import User


def ensure_schema_and_seed_data() -> None:
    """Đảm bảo bảng dishes có đủ cột is_active/status và chèn dữ liệu mẫu nếu DB đang trống."""
    inspector = inspect(engine)
    if "dishes" in inspector.get_table_names():
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
        db.commit()
    finally:
        db.close()
