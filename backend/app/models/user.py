"""Model bảng users (người dùng / khách hàng / admin)."""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="CUSTOMER", server_default="CUSTOMER")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

