"""Thư mục chứa các FastAPI dependencies dùng chung (lấy db session, kiểm tra đăng nhập/quyền...)."""
from app.db.session import get_db

__all__ = ["get_db"]

