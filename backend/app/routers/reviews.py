"""API đánh giá món sau khi nhận: /api/reviews

Quy tắc nghiệp vụ:
- Khách có đơn Hoàn thành (COMPLETED) được chấm sao, nhận xét (và ảnh) từng món một lần.
- Tính điểm trung bình và danh sách đánh giá của món.
- Cửa hàng trả lời đánh giá.
- Admin ẩn đánh giá vi phạm.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud import review as review_crud
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models.review import Review
from app.schemas.review import (
    DishReviewSummaryResponse,
    ReviewCreate,
    ReviewHideRequest,
    ReviewReplyRequest,
    ReviewResponse,
)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def _to_review_response(review: Review) -> ReviewResponse:
    """Helper chuyển đổi model Review sang ReviewResponse kèm tên món và tên người đánh giá."""
    return ReviewResponse(
        id=review.id,
        order_id=review.order_id,
        dish_id=review.dish_id,
        user_id=review.user_id,
        user_name=review.user.full_name if review.user else None,
        dish_name=review.dish.name if review.dish else None,
        rating=review.rating,
        content=review.content,
        image_url=review.image_url,
        shop_reply=review.shop_reply,
        replied_at=review.replied_at,
        is_hidden=review.is_hidden,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


# ── 1. Khách đánh giá món sau khi hoàn thành đơn ────────────────────────────
@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Khách đánh giá món ăn sau khi đơn hàng Hoàn thành",
)
def create_review(
    data: ReviewCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    review = review_crud.create_review(db=db, user_id=current_user_id, data=data)
    return _to_review_response(review)


# ── 2. Xem điểm trung bình và danh sách đánh giá của món ───────────────────
@router.get(
    "/dish/{dish_id}",
    response_model=DishReviewSummaryResponse,
    summary="Xem điểm trung bình và các nhận xét của một món ăn",
)
def get_dish_reviews(
    dish_id: int,
    include_hidden: bool = False,
    db: Session = Depends(get_db),
):
    dish, avg_rating, total_count, reviews = review_crud.get_dish_reviews_summary(
        db=db,
        dish_id=dish_id,
        include_hidden=include_hidden,
    )
    return DishReviewSummaryResponse(
        dish_id=dish.id,
        dish_name=dish.name,
        average_rating=avg_rating,
        total_reviews=total_count,
        reviews=[_to_review_response(r) for r in reviews],
    )


# ── 3. Cửa hàng trả lời đánh giá ───────────────────────────────────────────
@router.post(
    "/{review_id}/reply",
    response_model=ReviewResponse,
    summary="[Cửa hàng] Trả lời đánh giá của khách",
)
def reply_to_review(
    review_id: int,
    data: ReviewReplyRequest,
    role: str = Query(default="STAFF", description="Vai trò (STAFF hoặc ADMIN)"),
    db: Session = Depends(get_db),
):
    if role.upper() not in ("STAFF", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ nhân viên hoặc quản trị viên mới có quyền trả lời đánh giá",
        )
    review = review_crud.reply_to_review(db=db, review_id=review_id, shop_reply=data.shop_reply)
    return _to_review_response(review)


# ── 4. Admin ẩn đánh giá vi phạm ───────────────────────────────────────────
@router.patch(
    "/{review_id}/hide",
    response_model=ReviewResponse,
    summary="[Admin] Ẩn đánh giá vi phạm",
)
def hide_review(
    review_id: int,
    data: ReviewHideRequest,
    role: str = Query(default="ADMIN", description="Vai trò (ADMIN)"),
    db: Session = Depends(get_db),
):
    if role.upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản trị viên (ADMIN) mới có quyền ẩn đánh giá vi phạm",
        )
    review = review_crud.set_review_hidden_status(
        db=db,
        review_id=review_id,
        is_hidden=data.is_hidden,
    )
    return _to_review_response(review)


# ── 5. Lấy danh sách đánh giá theo đơn hàng ────────────────────────────────
@router.get(
    "/order/{order_id}",
    response_model=list[ReviewResponse],
    summary="Lấy danh sách các đánh giá của một đơn hàng",
)
def get_order_reviews(
    order_id: int,
    db: Session = Depends(get_db),
):
    reviews = review_crud.get_order_reviews(db=db, order_id=order_id)
    return [_to_review_response(r) for r in reviews]

