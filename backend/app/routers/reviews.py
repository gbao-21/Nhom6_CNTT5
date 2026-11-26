"""API đánh giá: /api/reviews

Phân quyền đơn giản:
- POST /api/reviews              -> Khách (đơn hàng và user_id không bắt buộc)
- GET  /api/reviews/dish/{id}   -> Public
- GET  /api/reviews/order/{id}  -> Public
- POST /api/reviews/{id}/reply  -> STAFF (role=STAFF qua query)
- PATCH /api/reviews/{id}/hide  -> ADMIN (role=ADMIN qua query)
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
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
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "reviews"
MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def require_staff(role: str = Query(default="STAFF")):
    if role.upper() not in ("STAFF", "ADMIN"):
        raise HTTPException(status_code=403, detail="Chỉ Staff/Admin mới có quyền này")


def require_admin(role: str = Query(default="ADMIN")):
    if role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền này")


# ── Khách: Tạo đánh giá ──────────────────────────────────────────────────────
@router.post(
    "",
    response_model=ReviewResponse,
    status_code=201,
    summary="Tạo đánh giá món (không bắt buộc đơn hàng)",
)
def create_review(data: ReviewCreate, db: Session = Depends(get_db)):
    return review_crud.create_review(db, data)


@router.post("/upload-image", summary="Tải ảnh đánh giá lên")
async def upload_review_image(file: UploadFile = File(...)):
    extension = ALLOWED_IMAGES.get(file.content_type)
    if extension is None:
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận ảnh JPG, PNG hoặc WEBP")

    content = await file.read(MAX_IMAGE_SIZE + 1)
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Dung lượng ảnh không được vượt quá 5MB")

    valid_image = (
        file.content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff")
    ) or (
        file.content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n")
    ) or (
        file.content_type == "image/webp"
        and content.startswith(b"RIFF")
        and content[8:12] == b"WEBP"
    )
    if not valid_image:
        raise HTTPException(status_code=400, detail="File tải lên không phải ảnh hợp lệ")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    (UPLOAD_DIR / filename).write_bytes(content)
    return {"image_url": f"/uploads/reviews/{filename}"}


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

