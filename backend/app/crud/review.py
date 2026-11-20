"""CRUD thao tác với bảng reviews."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.dish import Dish
from app.models.order import Order
from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewReplyRequest


def create_review(db: Session, data: ReviewCreate) -> Review:
    """Tạo đánh giá mới.

    Business rules:
    - Đánh giá không gắn đơn được tạo trực tiếp từ trang chi tiết món
    - Nếu có order_id, đơn phải COMPLETED, thuộc user và món chỉ được đánh giá 1 lần
    """
    if db.get(Dish, data.dish_id) is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy món ăn id={data.dish_id}")

    if data.order_id is not None:
        order = db.query(Order).filter(Order.id == data.order_id).first()
        if order is None:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn hàng id={data.order_id}")
        if order.status != "COMPLETED":
            raise HTTPException(status_code=400, detail="Chỉ có thể đánh giá đơn hàng đã hoàn thành")
        if order.user_id != data.user_id:
            raise HTTPException(status_code=403, detail="Bạn không có quyền đánh giá đơn hàng này")

        existing = (
            db.query(Review)
            .filter(Review.order_id == data.order_id, Review.dish_id == data.dish_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Món này trong đơn hàng đã được đánh giá trước đó")

    review = Review(
        order_id=data.order_id,
        dish_id=data.dish_id,
        user_id=data.user_id,
        rating=data.rating,
        content=data.content,
        image_url=data.image_url,
        is_hidden=False,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_dish_reviews(db: Session, dish_id: int) -> dict:
    """Lấy danh sách đánh giá của món, kèm điểm trung bình."""
    from app.models.dish import Dish
    from app.models.user import User

    dish = db.query(Dish).filter(Dish.id == dish_id).first()

    # Lấy các review không bị ẩn
    reviews = (
        db.query(Review)
        .filter(Review.dish_id == dish_id, Review.is_hidden == False)  # noqa: E712
        .order_by(Review.created_at.desc())
        .all()
    )

    # Gắn thêm user_name và dish_name
    result = []
    for r in reviews:
        item = {
            "id": r.id,
            "order_id": r.order_id,
            "dish_id": r.dish_id,
            "user_id": r.user_id,
            "user_name": None,
            "dish_name": dish.name if dish else None,
            "rating": r.rating,
            "content": r.content,
            "image_url": r.image_url,
            "shop_reply": r.shop_reply,
            "replied_at": r.replied_at,
            "is_hidden": r.is_hidden,
            "created_at": r.created_at,
        }
        if r.user_id:
            user = db.query(User).filter(User.id == r.user_id).first()
            if user:
                item["user_name"] = user.full_name or user.email
        result.append(item)

    total = len(result)
    avg = round(sum(r["rating"] for r in result) / total, 1) if total > 0 else 0.0

    return {
        "dish_id": dish_id,
        "dish_name": dish.name if dish else None,
        "average_rating": avg,
        "total_reviews": total,
        "reviews": result,
    }


def get_order_reviews(db: Session, order_id: int) -> dict:
    """Lấy danh sách đánh giá của đơn hàng."""
    from app.models.dish import Dish
    from app.models.user import User

    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn hàng id={order_id}")

    reviews = (
        db.query(Review)
        .filter(Review.order_id == order_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    result = []
    for r in reviews:
        dish = db.query(Dish).filter(Dish.id == r.dish_id).first() if r.dish_id else None
        user = db.query(User).filter(User.id == r.user_id).first() if r.user_id else None
        result.append({
            "id": r.id,
            "order_id": r.order_id,
            "dish_id": r.dish_id,
            "user_id": r.user_id,
            "user_name": (user.full_name or user.email) if user else None,
            "dish_name": dish.name if dish else None,
            "rating": r.rating,
            "content": r.content,
            "image_url": r.image_url,
            "shop_reply": r.shop_reply,
            "replied_at": r.replied_at,
            "is_hidden": r.is_hidden,
            "created_at": r.created_at,
        })

    return {
        "order_id": order_id,
        "order_status": order.status,
        "reviews": result,
    }


def reply_to_review(db: Session, review_id: int, data: ReviewReplyRequest) -> Review:
    """Cửa hàng trả lời đánh giá."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if review is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đánh giá id={review_id}")
    review.shop_reply = data.reply
    review.replied_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review


def set_review_hidden(db: Session, review_id: int, is_hidden: bool) -> Review:
    """Admin ẩn / hiện đánh giá."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if review is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đánh giá id={review_id}")
    review.is_hidden = is_hidden
    db.commit()
    db.refresh(review)
    return review

