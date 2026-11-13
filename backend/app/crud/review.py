"""CRUD xử lý nghiệp vụ Đánh giá (Review):
- Khách có đơn Hoàn thành được chấm sao, nhận xét (và ảnh) từng món một lần.
- Tính điểm trung bình của món.
- Cửa hàng trả lời đánh giá.
- Admin ẩn đánh giá vi phạm.
"""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.dish import Dish
from app.models.order import Order
from app.models.review import Review
from app.schemas.review import ReviewCreate


def get_review(db: Session, review_id: int) -> Optional[Review]:
    return db.get(Review, review_id)


def create_review(db: Session, user_id: int, data: ReviewCreate) -> Review:
    """Khách tạo đánh giá món ăn sau khi nhận hàng:
    - Đơn phải tồn tại và thuộc quyền sở hữu của khách.
    - Đơn phải ở trạng thái COMPLETED (Hoàn thành).
    - Món ăn phải nằm trong đơn hàng.
    - Mỗi món trong một đơn hàng chỉ được đánh giá duy nhất một lần.
    """
    order = db.get(Order, data.order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy đơn hàng id={data.order_id}",
        )

    if order.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chỉ có thể đánh giá đơn hàng của chính mình",
        )

    if order.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ có thể đánh giá khi đơn hàng đã Hoàn thành (COMPLETED). Trạng thái hiện tại: {order.status}",
        )

    dish = db.get(Dish, data.dish_id)
    if dish is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy món ăn id={data.dish_id}",
        )

    # Kiểm tra món ăn có nằm trong danh sách món của đơn hàng không
    dish_in_order = any(item.dish_id == data.dish_id for item in order.items)
    if not dish_in_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Món '{dish.name}' (id={data.dish_id}) không nằm trong đơn hàng {order.order_code}",
        )

    # Chặn đánh giá món đó lần 2 trong cùng đơn hàng
    existing_review = (
        db.query(Review)
        .filter(Review.order_id == data.order_id, Review.dish_id == data.dish_id)
        .first()
    )
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bạn đã đánh giá món '{dish.name}' trong đơn hàng này rồi. Mỗi món chỉ được đánh giá 1 lần.",
        )

    review = Review(
        order_id=data.order_id,
        dish_id=data.dish_id,
        user_id=user_id,
        rating=data.rating,
        content=data.content,
        image_url=data.image_url,
        is_hidden=False,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_dish_reviews_summary(
    db: Session,
    dish_id: int,
    include_hidden: bool = False,
) -> tuple[Dish, float, int, list[Review]]:
    """Lấy danh sách đánh giá và tính điểm trung bình của một món ăn."""
    dish = db.get(Dish, dish_id)
    if dish is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy món ăn id={dish_id}",
        )

    query = db.query(Review).filter(Review.dish_id == dish_id)
    if not include_hidden:
        query = query.filter(Review.is_hidden.is_(False))

    reviews = query.order_by(Review.created_at.desc()).all()
    total_reviews = len(reviews)
    if total_reviews > 0:
        average_rating = round(sum(r.rating for r in reviews) / total_reviews, 1)
    else:
        average_rating = 0.0

    return dish, average_rating, total_reviews, reviews


def reply_to_review(db: Session, review_id: int, shop_reply: str) -> Review:
    """Cửa hàng trả lời đánh giá."""
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy đánh giá id={review_id}",
        )

    review.shop_reply = shop_reply
    review.replied_at = datetime.now()
    db.commit()
    db.refresh(review)
    return review


def set_review_hidden_status(db: Session, review_id: int, is_hidden: bool = True) -> Review:
    """Admin ẩn hoặc hiện lại đánh giá vi phạm."""
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy đánh giá id={review_id}",
        )

    review.is_hidden = is_hidden
    db.commit()
    db.refresh(review)
    return review


def get_order_reviews(db: Session, order_id: int) -> list[Review]:
    """Lấy danh sách các đánh giá của 1 đơn hàng."""
    return db.query(Review).filter(Review.order_id == order_id).all()

