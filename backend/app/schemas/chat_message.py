from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Tạo tin nhắn mới ────────────────────────────────────────────────────────
class ChatMessageCreate(BaseModel):
    customer_id: int = Field(description="ID khách hàng (cuộc trò chuyện của khách)")
    content: str = Field(min_length=1, max_length=5000, description="Nội dung tin nhắn")
    sender_role: Optional[str] = Field(default="CUSTOMER", description="Vai trò người gửi: CUSTOMER, STAFF, ADMIN")


# ── Cập nhật trạng thái đọc tin nhắn ───────────────────────────────────────
class ChatMessageMarkRead(BaseModel):
    is_read: bool = Field(default=True, description="Đánh dấu tin nhắn đã đọc")


# ── Response tin nhắn ───────────────────────────────────────────────────────
class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    sender_id: int
    sender_role: str
    content: str
    is_read: bool
    created_at: datetime

