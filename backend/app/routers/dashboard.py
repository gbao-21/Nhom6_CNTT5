"""API thống kê Dashboard Admin: /api/dashboard"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.crud import dashboard as dashboard_crud
from app.db.session import get_db
from app.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Lấy toàn bộ thống kê Dashboard Admin (doanh thu, đơn hàng, món bán chạy, đánh giá, mã giảm giá)",
)
def get_dashboard_overview(
    period: str = Query(default="day", description="Nhóm doanh thu theo 'day' (ngày) hoặc 'month' (tháng)"),
    start_date: Optional[date] = Query(default=None, description="Từ ngày (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(default=None, description="Đến ngày (YYYY-MM-DD)"),
    top_limit: int = Query(default=5, ge=1, le=20, description="Số lượng món bán chạy hiển thị"),
    db: Session = Depends(get_db),
):
    return dashboard_crud.get_dashboard_statistics(
        db=db,
        period=period,
        start_date=start_date,
        end_date=end_date,
        top_limit=top_limit,
    )
