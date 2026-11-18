"""API đánh giá: /api/reviews

Phân quyền đơn giản:
- POST /api/reviews              -> Khách (truyền user_id trong body)
- GET  /api/reviews/dish/{id}   -> Public
- GET  /api/reviews/order/{id}  -> Public
- POST /api/reviews/{id}/reply  -> STAFF (role=STAFF qua query)
- PATCH /api/reviews/{id}/hide  -> ADMIN (role=ADMIN qua query)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import review as review_crud
from app.db.session import get_db
from app.schemas.review import (
    DishReviewSummaryResponse,
    OrderReviewResponse,
    ReviewCreate,
    ReviewHideRequest,
    ReviewReplyRequest,
    ReviewResponse,
)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def require_staff(role: str = Query(default="STAFF")):
    if role.upper() not in ("STAFF", "ADMIN"):
        raise HTTPException(status_code=403, detail="Chỉ Staff/Admin mới có quyền này")


def require_admin(role: str = Query(default="ADMIN")):
    if role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền này")


# ── Khách: Tạo đánh giá ──────────────────────────────────────────────────────
@router.post("", response_model=ReviewResponse, status_code=201, summary="Tạo đánh giá món")
def create_review(data: ReviewCreate, db: Session = Depends(get_db)):
    return review_crud.create_review(db, data)


# ── Public: Đánh giá theo món ────────────────────────────────────────────────
@router.get(
    "/dish/{dish_id}",
    response_model=DishReviewSummaryResponse,
    summary="Danh sách đánh giá của món + điểm trung bình",
)
def get_dish_reviews(dish_id: int, db: Session = Depends(get_db)):
    return review_crud.get_dish_reviews(db, dish_id)


# ── Public: Đánh giá theo đơn ────────────────────────────────────────────────
@router.get(
    "/order/{order_id}",
    response_model=OrderReviewResponse,
    summary="Danh sách đánh giá của đơn hàng",
)
def get_order_reviews(order_id: int, db: Session = Depends(get_db)):
    return review_crud.get_order_reviews(db, order_id)


# ── Staff: Trả lời đánh giá ──────────────────────────────────────────────────
@router.post(
    "/{review_id}/reply",
    response_model=ReviewResponse,
    summary="[Staff] Trả lời đánh giá",
    dependencies=[Depends(require_staff)],
)
def reply_review(review_id: int, data: ReviewReplyRequest, db: Session = Depends(get_db)):
    return review_crud.reply_to_review(db, review_id, data)


# ── Admin: Ẩn / hiện đánh giá ────────────────────────────────────────────────
@router.patch(
    "/{review_id}/hide",
    response_model=ReviewResponse,
    summary="[Admin] Ẩn hoặc hiện đánh giá vi phạm",
    dependencies=[Depends(require_admin)],
)
def hide_review(review_id: int, data: ReviewHideRequest, db: Session = Depends(get_db)):
    return review_crud.set_review_hidden(db, review_id, data.is_hidden)

