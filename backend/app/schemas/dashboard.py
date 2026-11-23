"""Pydantic schemas cho Dashboard thống kê Admin."""
from typing import Optional
from pydantic import BaseModel


class RevenuePoint(BaseModel):
    label: str
    revenue: float
    order_count: int


class OrderStatusCount(BaseModel):
    status: str
    label: str
    count: int


class BestSellingDish(BaseModel):
    dish_id: Optional[int] = None
    dish_name: str
    total_quantity: int
    total_revenue: float


class CouponUsageItem(BaseModel):
    code: str
    used_count: int
    discount_type: str
    discount_value: float


class DashboardResponse(BaseModel):
    period: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_revenue: float
    total_orders: int
    completed_orders: int
    average_rating: float
    total_reviews: int
    total_coupons_used: int
    revenue_series: list[RevenuePoint]
    orders_by_status: list[OrderStatusCount]
    best_selling_dishes: list[BestSellingDish]
    coupon_usages: list[CouponUsageItem]
