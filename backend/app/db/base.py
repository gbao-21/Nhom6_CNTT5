"""Khai báo Base dùng chung cho toàn bộ SQLAlchemy models."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Mọi model (bảng) đều kế thừa từ Base."""
