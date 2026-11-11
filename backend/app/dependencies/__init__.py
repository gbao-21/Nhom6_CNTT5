"""Thư mục chứa các FastAPI dependencies dùng chung (lấy db session, xác định user hiện tại...)."""
import base64
import json

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User


def _extract_user_id_from_bearer(authorization: str | None) -> int | None:
    """Đọc user_id từ header Authorization: Bearer <token> (nếu có)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    if token.isdigit():
        return int(token)
    # Thử giải mã payload JWT (phần thứ 2 của header.payload.signature)
    parts = token.split(".")
    if len(parts) == 3:
        try:
            payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
            uid = payload.get("user_id") or payload.get("sub") or payload.get("id")
            if uid is not None and str(uid).isdigit():
                return int(uid)
        except Exception:  # noqa: BLE001
            return None
    return None


def get_current_user_id(
    x_user_id: int | None = Header(
        default=None,
        alias="X-User-Id",
        description="ID người dùng đang đăng nhập (Header X-User-Id)",
    ),
    user_id: int | None = Query(
        default=None,
        description="ID người dùng đang đăng nhập (Query param hỗ trợ test trên Swagger)",
    ),
    authorization: str | None = Header(default=None, include_in_schema=False),
    db: Session = Depends(get_db),
) -> int:
    """Lấy user_id của người dùng hiện tại để đảm bảo chỉ thao tác trên giỏ của mình.

    Thứ tự ưu tiên:
    1. Header `X-User-Id`
    2. Header `Authorization: Bearer <token>`
    3. Query parameter `user_id`
    4. Mặc định `user_id = 1` khi test nhanh nếu không truyền
    """
    resolved_id = x_user_id or _extract_user_id_from_bearer(authorization) or user_id or 1
    if resolved_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin người dùng không hợp lệ",
        )

    user = db.get(User, resolved_id)
    if user is not None and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản người dùng đã bị khóa",
        )
    return resolved_id


__all__ = ["get_db", "get_current_user_id"]
