"""Tương thích ngược: re-export kết nối DB từ app.db.session để tránh lệch cấu hình."""
from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db

__all__ = ["Base", "SessionLocal", "engine", "get_db"]
