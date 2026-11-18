"""API phục vụ trang thực đơn khách hàng: /api/menu."""
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.category import Category
from app.models.dish import Dish
from app.schemas.category import CategoryResponse
from app.schemas.dish import DishResponse
from app.schemas.menu import (
    MenuCategoryResponse,
    MenuDishListResponse,
    MenuOverviewResponse,
)

router = APIRouter(prefix="/menu", tags=["Menu"])


@router.get("/categories", response_model=list[CategoryResponse])
def list_menu_categories(db: Session = Depends(get_db)):
    categories = db.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.id.asc())
    ).all()
    return categories


@router.get("/dishes", response_model=MenuDishListResponse)
def list_menu_dishes(
    is_available: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    category_id: int | None = Query(default=None, ge=1),
    sort_by: str | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    filters = [Dish.is_active.is_(True)]
    if is_available is not None:
        filters.append(Dish.is_available.is_(is_available))
    if search:
        filters.append(Dish.name.contains(search))
    if category_id is not None:
        filters.append(Dish.category_id == category_id)
    if min_price is not None:
        filters.append(Dish.price >= min_price)
    if max_price is not None:
        filters.append(Dish.price <= max_price)

    count_query = select(func.count()).select_from(Dish).where(*filters)
    total = db.scalar(count_query) or 0

    query = select(Dish).where(*filters).options(selectinload(Dish.options))
    if sort_by == "price_asc":
        query = query.order_by(Dish.price.asc(), Dish.id.desc())
    elif sort_by == "price_desc":
        query = query.order_by(Dish.price.desc(), Dish.id.desc())
    elif sort_by == "newest":
        query = query.order_by(Dish.created_at.desc(), Dish.id.desc())
    else:
        query = query.order_by(Dish.id.desc())

    dishes = db.scalars(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()
    return MenuDishListResponse(
        items=[DishResponse.model_validate(dish) for dish in dishes],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/overview", response_model=MenuOverviewResponse)
def get_menu_overview(db: Session = Depends(get_db)):
    categories = db.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.id.asc())
        .options(selectinload(Category.dishes).selectinload(Dish.options))
    ).all()
    active_categories = [
        MenuCategoryResponse(
            id=category.id,
            name=category.name,
            description=category.description,
            is_active=category.is_active,
            dishes=[
                DishResponse.model_validate(dish)
                for dish in category.dishes
                if dish.is_active
            ],
        )
        for category in categories
    ]
    return MenuOverviewResponse(categories=active_categories)
