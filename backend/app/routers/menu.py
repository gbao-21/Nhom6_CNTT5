"""API đọc thực đơn dành cho khách hàng: /api/menu"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
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
def _visible_dish_query():
    return (
        select(Dish)
        .join(Category, Dish.category_id == Category.id)
        .where(
            Category.is_active.is_(True),
            Dish.is_active.is_(True),
            Dish.status != "HIDDEN",
        )
        .options(selectinload(Dish.options))
    )


def _dish_response(dish: Dish) -> dict:
    return {
        "id": dish.id,
        "category_id": dish.category_id,
        "name": dish.name,
        "description": dish.description,
        "price": Decimal(dish.price),
        "image_url": dish.image_url,
        "is_available": dish.is_available and dish.status != "OUT_OF_STOCK",
        "is_active": dish.is_active,
        "status": dish.status,
        "options": dish.options,
        "created_at": dish.created_at,
        "updated_at": dish.updated_at,
    }


@router.get("", name="get_menu")
@router.get("/overview", name="get_menu_overview")
def get_menu_overview(db: Session = Depends(get_db)):
    """Trả về menu theo danh mục, dùng trực tiếp bởi trang thực đơn."""
    categories = db.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .options(
            selectinload(
                Category.dishes.and_(
                    Dish.is_active.is_(True),
                    Dish.status != "HIDDEN",
                )
            ).selectinload(Dish.options)
        )
        .order_by(Category.id.asc())
    ).all()

    return {
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "dishes": [_dish_response(dish) for dish in category.dishes],
            }
            for category in categories
        ]
    }


@router.get("/categories", response_model=list[CategoryResponse])
def get_menu_categories(db: Session = Depends(get_db)):
    """Liệt kê các danh mục đang được hiển thị trên menu."""
    return db.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.id.asc())
    ).all()


@router.get("/dishes", response_model=list[DishResponse], name="get_menu_dishes")
@router.get("/items", response_model=list[DishResponse], name="get_menu_items")
def get_menu_dishes(
    category_id: int | None = Query(default=None, ge=1),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Liệt kê món đang hiển thị; có thể lọc theo danh mục hoặc tên món."""
    query = _visible_dish_query()
    if category_id is not None:
        query = query.where(Dish.category_id == category_id)
    if q and q.strip():
        query = query.where(Dish.name.contains(q.strip()))

    dishes = db.scalars(query.order_by(Dish.id.asc())).all()
    return [_dish_response(dish) for dish in dishes]


@router.get(
    "/dishes/{dish_id}",
    response_model=DishResponse,
    name="get_menu_dish_detail",
)
@router.get(
    "/items/{dish_id}",
    response_model=DishResponse,
    name="get_menu_item_detail",
)
def get_menu_dish_detail(dish_id: int, db: Session = Depends(get_db)):
    """Lấy chi tiết một món đang hiển thị trên menu."""
    dish = db.scalars(
        _visible_dish_query().where(Dish.id == dish_id)
    ).first()
    if dish is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy món ăn")
    return _dish_response(dish)
