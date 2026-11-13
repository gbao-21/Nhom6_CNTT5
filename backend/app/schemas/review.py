from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Khách tạo đánh giá ──────────────────────────────────────────────────────
class ReviewCreate(BaseModel):
    order_id: int = Field(description="ID đơn hàng được đánh giá")
    dish_id: Optional[int] = Field(default=None, description="ID món ăn (tuỳ chọn)")
    rating: int = Field(ge=1, le=5, description="Số sao đánh giá từ 1 đến 5")
    content: Optional[str] = Field(default=None, max_length=2000, description="Nội dung đánh giá")
    image_url: Optional[str] = Field(default=None, max_length=500, description="URL ảnh thực tế món ăn")


# ── Cửa hàng phản hồi đánh giá ──────────────────────────────────────────────
class ReviewReplyRequest(BaseModel):
    shop_reply: str = Field(min_length=1, max_length=2000, description="Nội dung phản hồi của cửa hàng")


# ── Cập nhật đánh giá ───────────────────────────────────────────────────────
class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    content: Optional[str] = Field(default=None, max_length=2000)
    image_url: Optional[str] = Field(default=None, max_length=500)


# ── Response đánh giá ───────────────────────────────────────────────────────
class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    dish_id: Optional[int] = None
    user_id: int
    rating: int
    content: Optional[str] = None
    image_url: Optional[str] = None
    shop_reply: Optional[str] = None
    replied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

