"""CRUD cho bảng users và hàm lấy phí ship theo khu vực (module Tài khoản)."""
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.delivery_area import DeliveryArea
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def get_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id.desc())))


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, data: UserCreate) -> User:
    payload = data.model_dump()
    password = payload.pop("password")
    user = User(**payload, password_hash=password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def get_shipping_fee_by_area(
    db: Session,
    delivery_area_id: int | None = None,
    user_id: int | None = None,
) -> Decimal:
    """Hàm của module Tài khoản: Tính phí ship theo khu vực giao hàng (delivery_area_id).

    - Nếu truyền `delivery_area_id`: lấy phí ship từ bảng `delivery_areas`.
    - Nếu không truyền `delivery_area_id`: kiểm tra xem user có khu vực mặc định không, nếu không thì phí ship = 0.
    """
    resolved_area_id = delivery_area_id
    if resolved_area_id is None and user_id is not None:
        user = db.get(User, user_id)
        resolved_area_id = getattr(user, "delivery_area_id", None) if user else None

    if resolved_area_id is None:
        return Decimal("0")

    area = db.get(DeliveryArea, resolved_area_id)
    if area is None or not getattr(area, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Khu vực giao hàng id={resolved_area_id} không tồn tại hoặc tạm ngưng phục vụ",
        )

    return Decimal(str(area.shipping_fee or 0))
