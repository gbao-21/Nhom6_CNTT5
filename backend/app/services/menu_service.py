from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.crud import crud_menu
from app.schemas.menu import (
    CustomerMenuOverviewOut,
    MenuCategoryWithDishesOut,
    MenuDishDetailOut,
)


def get_customer_menu_overview(db: Session) -> CustomerMenuOverviewOut:
    categories = crud_menu.get_active_categories(db)
    dishes = crud_menu.get_available_dishes(db, limit=500)

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


def get_customer_dish_detail(db: Session, dish_id: int) -> MenuDishDetailOut:
    dish = crud_menu.get_available_dish_by_id(db, dish_id=dish_id)
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Món ăn không tồn tại hoặc hiện đã ngừng phục vụ.",
        )
    return dish