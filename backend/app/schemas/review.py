"""Pydantic schemas cho Reviews."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    order_id: Optional[int] = None
    dish_id: int
    user_id: Optional[int] = None
    rating: int = Field(..., ge=1, le=5)
    content: Optional[str] = None
    image_url: Optional[str] = None


class ReviewReplyRequest(BaseModel):
    reply: str


class ReviewHideRequest(BaseModel):
    is_hidden: bool


class ReviewResponse(BaseModel):
    id: int
    order_id: Optional[int] = None
    dish_id: Optional[int] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    dish_name: Optional[str] = None
    rating: int
    content: Optional[str] = None
    image_url: Optional[str] = None
    shop_reply: Optional[str] = None
    replied_at: Optional[datetime] = None
    is_hidden: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DishReviewSummaryResponse(BaseModel):
    dish_id: int
    dish_name: Optional[str] = None
    average_rating: float
    total_reviews: int
    reviews: list[ReviewResponse]


class OrderReviewResponse(BaseModel):
    order_id: int
    order_status: str
    reviews: list[ReviewResponse]

