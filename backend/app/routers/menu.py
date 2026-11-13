from decimal import Decimal
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.crud import crud_menu
from app.services import menu_service
from app.schemas.menu import (
    CustomerMenuOverviewOut,
    MenuCategoryBriefOut,
    MenuDishDetailOut,
    MenuDishOut,
    PaginatedMenuDishesOut,
)

router = APIRouter(prefix="/menu", tags=["Menu"])

SortOption = Literal["price_asc", "price_desc", "bestseller", "rating", "newest"]


@router.get("", response_model=CustomerMenuOverviewOut)
@router.get("/overview", response_model=CustomerMenuOverviewOut)
def get_menu_overview(db: Session = Depends(get_db)):
    """Lấy tổng quan menu gồm danh mục và các món ăn tương ứng."""
    return menu_service.get_customer_menu_overview(db)


@router.get("/categories", response_model=List[MenuCategoryBriefOut])
def get_menu_categories(db: Session = Depends(get_db)):
    """Lấy danh sách các danh mục đang hoạt động."""
    return crud_menu.get_active_categories(db)


@router.get("/dishes", response_model=PaginatedMenuDishesOut)
@router.get("/search", response_model=PaginatedMenuDishesOut)
def search_and_filter_dishes(
    search: Optional[str] = Query(None, description="Tìm món ăn theo tên hoặc mô tả"),
    category_id: Optional[int] = Query(None, ge=1, description="ID danh mục (VD: 1, 2)"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Giá tối thiểu (VD: 10000)"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Giá tối đa (VD: 100000)"),
    is_available: Optional[bool] = Query(True, description="Trạng thái còn bán (true/false)"),
    sort_by: Optional[SortOption] = Query(
        None,
        description="Sắp xếp: price_asc (giá tăng), price_desc (giá giảm), bestseller (bán chạy), rating (đánh giá), newest (mới nhất)",
    ),
    page: int = Query(1, ge=1, description="Trang hiện tại (bắt đầu từ 1)"),
    page_size: int = Query(12, ge=1, le=100, description="Số món trên mỗi trang"),
    db: Session = Depends(get_db),
):
    """API tìm theo tên, lọc danh mục/khoảng giá/còn bán, sắp xếp và phân trang."""
    return menu_service.get_paginated_menu_dishes(
        db=db,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        is_available=is_available,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@router.get("/items", response_model=List[MenuDishOut])
def get_menu_items(
    search: Optional[str] = Query(None, description="Tìm theo tên món"),
    category_id: Optional[int] = Query(None, ge=1, description="ID danh mục"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Giá tối thiểu"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Giá tối đa"),
    is_available: Optional[bool] = Query(True, description="Lọc món còn bán"),
    sort_by: Optional[SortOption] = Query(None, description="Tiêu chí sắp xếp"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lấy danh sách món ăn dạng mảng phẳng."""
    page = (skip // limit) + 1 if limit > 0 else 1
    items, _ = crud_menu.search_and_filter_dishes(
        db=db,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        is_available=is_available,
        sort_by=sort_by,
        page=page,
        page_size=limit,
    )
    return items


@router.get("/dishes/{dish_id}", response_model=MenuDishDetailOut)
@router.get("/items/{dish_id}", response_model=MenuDishDetailOut)
def get_menu_dish_detail(
    dish_id: int,
    db: Session = Depends(get_db),
):
    """Lấy chi tiết món ăn kèm danh mục và các nhóm tuỳ chọn."""
    return menu_service.get_customer_dish_detail(db=db, dish_id=dish_id)