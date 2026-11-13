import math
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.crud import crud_menu
from app.schemas.menu import (
    CustomerMenuOverviewOut,
    MenuCategoryWithDishesOut,
    MenuDishDetailOut,
    MenuDishOptionOut,
    MenuOptionGroupOut,
    PaginatedMenuDishesOut,
)


def get_customer_menu_overview(db: Session) -> CustomerMenuOverviewOut:
    categories = crud_menu.get_active_categories(db)
    dishes, _ = crud_menu.search_and_filter_dishes(
        db=db, is_available=True, page=1, page_size=500
    )

    dishes_by_category = {}
    for dish in dishes:
        if dish.category_id is not None:
            dishes_by_category.setdefault(dish.category_id, []).append(dish)

    category_list: List[MenuCategoryWithDishesOut] = []
    for cat in categories:
        cat_dishes = dishes_by_category.get(cat.id, [])
        category_list.append(
            MenuCategoryWithDishesOut(
                id=cat.id,
                name=cat.name,
                description=cat.description,
                dishes=cat_dishes,
            )
        )

    return CustomerMenuOverviewOut(
        categories=category_list,
        total_categories=len(category_list),
        total_dishes=len(dishes),
    )


def get_paginated_menu_dishes(
    db: Session,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    is_available: Optional[bool] = True,
    sort_by: Optional[str] = None,
    page: int = 1,
    page_size: int = 12,
) -> PaginatedMenuDishesOut:
    items, total = crud_menu.search_and_filter_dishes(
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
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedMenuDishesOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_customer_dish_detail(db: Session, dish_id: int) -> MenuDishDetailOut:
    dish = crud_menu.get_available_dish_by_id(db, dish_id=dish_id)
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Món ăn không tồn tại hoặc hiện đã ngừng phục vụ.",
        )

    option_items = [
        MenuDishOptionOut.model_validate(opt) for opt in dish.options if opt.is_available
    ]
    option_groups: List[MenuOptionGroupOut] = []
    if option_items:
        option_groups.append(
            MenuOptionGroupOut(
                group_name="Tuỳ chọn thêm",
                is_required=False,
                min_choices=0,
                max_choices=len(option_items),
                items=option_items,
            )
        )

    return MenuDishDetailOut(
        id=dish.id,
        category_id=dish.category_id,
        name=dish.name,
        description=dish.description,
        price=dish.price,
        image_url=dish.image_url,
        is_available=dish.is_available,
        sold_count=getattr(dish, "sold_count", 0),
        rating=getattr(dish, "rating", 5.0),
        options=option_items,
        category=dish.category,
        option_groups=option_groups,
        created_at=dish.created_at,
        updated_at=dish.updated_at,
    )