from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Khách tạo đánh giá món sau khi nhận ──────────────────────────────────────
class ReviewCreate(BaseModel):
    order_id: int = Field(description="ID đơn hàng đã hoàn thành")
    dish_id: int = Field(description="ID món ăn trong đơn hàng được đánh giá")
    rating: int = Field(ge=1, le=5, description="Số sao đánh giá từ 1 đến 5 sao")
    content: Optional[str] = Field(default=None, max_length=2000, description="Nhận xét của khách")
    image_url: Optional[str] = Field(default=None, max_length=500, description="URL ảnh thực tế món ăn")


# ── Cửa hàng phản hồi đánh giá ──────────────────────────────────────────────
class ReviewReplyRequest(BaseModel):
    shop_reply: str = Field(min_length=1, max_length=2000, description="Nội dung phản hồi của cửa hàng")


# ── Admin ẩn / hiện đánh giá vi phạm ────────────────────────────────────────
class ReviewHideRequest(BaseModel):
    is_hidden: bool = Field(default=True, description="True = ẩn đánh giá, False = hiện đánh giá")
    reason: Optional[str] = Field(default=None, max_length=500, description="Lý do ẩn đánh giá vi phạm")


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
    user_name: Optional[str] = None
    dish_name: Optional[str] = None
    rating: int
    content: Optional[str] = None
    image_url: Optional[str] = None
    shop_reply: Optional[str] = None
    replied_at: Optional[datetime] = None
    is_hidden: bool = False
    created_at: datetime
    updated_at: datetime


# ── Response Điểm trung bình và danh sách đánh giá của món ───────────────────
class DishReviewSummaryResponse(BaseModel):
    dish_id: int
    dish_name: Optional[str] = None
    average_rating: float = Field(description="Điểm trung bình của món (1.0 - 5.0)")
    total_reviews: int = Field(description="Tổng số lượng đánh giá hợp lệ (không bị ẩn)")
    reviews: list[ReviewResponse] = Field(default_factory=list, description="Danh sách các đánh giá")
