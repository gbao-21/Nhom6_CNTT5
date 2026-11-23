"""CRUD tổng hợp số liệu thống kê cho Dashboard Admin."""
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.coupon import Coupon
from app.models.order import Order, OrderItem
from app.models.review import Review

ORDER_STATUS_LABELS = {
    "PENDING": "Chờ xác nhận",
    "CONFIRMED": "Đã xác nhận",
    "PREPARING": "Đang chuẩn bị",
    "DELIVERING": "Đang giao",
    "COMPLETED": "Hoàn thành",
    "CANCELLED": "Đã huỷ",
}


def _parse_date_bounds(
    start_date: Optional[date],
    end_date: Optional[date],
) -> tuple[Optional[datetime], Optional[datetime]]:
    start_dt = datetime.combine(start_date, time.min) if start_date else None
    end_dt = datetime.combine(end_date, time.max) if end_date else None
    return start_dt, end_dt


def get_dashboard_statistics(
    db: Session,
    period: str = "day",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    top_limit: int = 5,
) -> dict:
    """Tính toán toàn bộ chỉ số thống kê Dashboard Admin."""
    period_mode = "month" if period == "month" else "day"
    start_dt, end_dt = _parse_date_bounds(start_date, end_date)

    # 1. Lọc đơn hàng theo khoảng thời gian
    order_query = db.query(Order)
    if start_dt:
        order_query = order_query.filter(Order.created_at >= start_dt)
    if end_dt:
        order_query = order_query.filter(Order.created_at <= end_dt)

    orders = order_query.order_by(Order.created_at.asc()).all()

    total_orders = len(orders)
    completed_orders = sum(1 for o in orders if o.status == "COMPLETED")
    valid_orders = [o for o in orders if o.status != "CANCELLED"]
    total_revenue = float(sum(float(o.total_amount or 0) for o in valid_orders))

    # 2. Doanh thu theo ngày hoặc theo tháng
    revenue_buckets: dict[str, dict] = {}
    for o in valid_orders:
        created = o.created_at or datetime.now()
        key = created.strftime("%Y-%m") if period_mode == "month" else created.strftime("%Y-%m-%d")
        if key not in revenue_buckets:
            revenue_buckets[key] = {"label": key, "revenue": 0.0, "order_count": 0}
        revenue_buckets[key]["revenue"] += float(o.total_amount or 0)
        revenue_buckets[key]["order_count"] += 1

    revenue_series = [
        {
            "label": item["label"],
            "revenue": round(item["revenue"], 2),
            "order_count": item["order_count"],
        }
        for item in sorted(revenue_buckets.values(), key=lambda x: x["label"])
    ]

    # 3. Số đơn theo trạng thái
    status_counts = {st: 0 for st in ORDER_STATUS_LABELS}
    for o in orders:
        st = (o.status or "PENDING").upper()
        status_counts[st] = status_counts.get(st, 0) + 1

    orders_by_status = [
        {
            "status": st,
            "label": ORDER_STATUS_LABELS.get(st, st),
            "count": cnt,
        }
        for st, cnt in status_counts.items()
    ]

    # 4. Món bán chạy (tính từ order_items của các đơn không bị huỷ)
    item_query = (
        db.query(
            OrderItem.dish_id,
            OrderItem.dish_name,
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.line_total).label("total_rev"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status != "CANCELLED")
    )
    if start_dt:
        item_query = item_query.filter(Order.created_at >= start_dt)
    if end_dt:
        item_query = item_query.filter(Order.created_at <= end_dt)

    best_rows = (
        item_query.group_by(OrderItem.dish_id, OrderItem.dish_name)
        .order_by(func.sum(OrderItem.quantity).desc(), func.sum(OrderItem.line_total).desc())
        .limit(top_limit)
        .all()
    )

    best_selling_dishes = [
        {
            "dish_id": row.dish_id,
            "dish_name": row.dish_name,
            "total_quantity": int(row.total_qty or 0),
            "total_revenue": round(float(row.total_rev or 0), 2),
        }
        for row in best_rows
    ]

    # 5. Điểm đánh giá trung bình
    review_query = db.query(Review).filter(Review.is_hidden == False)  # noqa: E712
    if start_dt:
        review_query = review_query.filter(Review.created_at >= start_dt)
    if end_dt:
        review_query = review_query.filter(Review.created_at <= end_dt)

    reviews = review_query.all()
    total_reviews = len(reviews)
    average_rating = (
        round(sum(int(r.rating or 0) for r in reviews) / total_reviews, 2)
        if total_reviews > 0
        else 0.0
    )

    # 6. Số mã giảm giá đã dùng
    order_coupon_counts: dict[str, int] = {}
    for o in valid_orders:
        if o.coupon_code and o.coupon_code.strip():
            code = o.coupon_code.strip().upper()
            order_coupon_counts[code] = order_coupon_counts.get(code, 0) + 1

    all_coupons = db.query(Coupon).order_by(Coupon.used_count.desc(), Coupon.id.asc()).all()
    coupon_usages = []
    seen_codes = set()

    for c in all_coupons:
        code_upper = c.code.upper()
        seen_codes.add(code_upper)
        # Nếu lọc theo ngày thì ưu tiên số đơn dùng mã trong khoảng ngày đó; nếu không lọc ngày thì lấy max giữa used_count và số đơn thực tế
        if start_dt or end_dt:
            used_cnt = order_coupon_counts.get(code_upper, 0)
        else:
            used_cnt = max(int(c.used_count or 0), order_coupon_counts.get(code_upper, 0))

        coupon_usages.append(
            {
                "code": c.code,
                "used_count": used_cnt,
                "discount_type": c.discount_type,
                "discount_value": float(c.discount_value or 0),
            }
        )

    for code_upper, cnt in order_coupon_counts.items():
        if code_upper not in seen_codes:
            coupon_usages.append(
                {
                    "code": code_upper,
                    "used_count": cnt,
                    "discount_type": "FIXED",
                    "discount_value": 0.0,
                }
            )

    total_coupons_used = sum(item["used_count"] for item in coupon_usages)

    return {
        "period": period_mode,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "average_rating": average_rating,
        "total_reviews": total_reviews,
        "total_coupons_used": total_coupons_used,
        "revenue_series": revenue_series,
        "orders_by_status": orders_by_status,
        "best_selling_dishes": best_selling_dishes,
        "coupon_usages": coupon_usages,
    }
