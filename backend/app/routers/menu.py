"""API đọc thực đơn dành cho khách hàng: /api/menu"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.category import Category
from app.models.dish import Dish
from app.schemas.category import CategoryResponse
from app.schemas.dish import DishResponse
from app.schemas.menu import (
    MenuDishListResponse,
    MenuOverviewResponse,
)

router = APIRouter(prefix="/menu", tags=["Menu"])


def _visible_dish_filters():
    return [
        Category.is_active.is_(True),
        Dish.is_active.is_(True),
        Dish.status != "HIDDEN",
    ]


def _visible_dish_query():
    return (
        select(Dish)
        .join(Category, Dish.category_id == Category.id)
        .where(*_visible_dish_filters())
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


@router.get("", response_model=MenuOverviewResponse, name="get_menu")
@router.get("/overview", response_model=MenuOverviewResponse, name="get_menu_overview")
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
                "description": category.description,
                "is_active": category.is_active,
                "dishes": [
                    DishResponse.model_validate(_dish_response(dish))
                    for dish in category.dishes
                ],
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


@router.get(
    "/dishes",
    response_model=MenuDishListResponse | list[DishResponse],
    name="get_menu_dishes",
)
def get_menu_dishes(
    is_available: bool | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    search: str | None = None,
    category_id: int | None = Query(default=None, ge=1),
    q: str | None = Query(default=None),
    sort_by: str | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    """Liệt kê món đang hiển thị; hỗ trợ cả dạng cũ và phân trang cho frontend."""
    filters = _visible_dish_filters()
    query_filters = []
    if category_id is not None:
        query_filters.append(Dish.category_id == category_id)
    keyword = search if search is not None else q
    if keyword and keyword.strip():
        query_filters.append(Dish.name.contains(keyword.strip()))
    if is_available is True:
        query_filters.extend(
            [Dish.is_available.is_(True), Dish.status != "OUT_OF_STOCK"]
        )
    elif is_available is False:
        query_filters.append(
            or_(Dish.is_available.is_(False), Dish.status == "OUT_OF_STOCK")
        )
    if min_price is not None:
        query_filters.append(Dish.price >= min_price)
    if max_price is not None:
        query_filters.append(Dish.price <= max_price)

    query = _visible_dish_query().where(*query_filters)
    filters.extend(query_filters)
    uses_pagination = any(
        value is not None
        for value in (is_available, page, page_size, search, sort_by, min_price, max_price)
    )
    if not uses_pagination:
        return [
            _dish_response(dish)
            for dish in db.scalars(query.order_by(Dish.id.asc())).all()
        ]

    page_number = page or 1
    result_page_size = page_size or 50
    count_query = (
        select(func.count(Dish.id))
        .select_from(Dish)
        .join(Category, Dish.category_id == Category.id)
        .where(*filters)
    )
    total = db.scalar(count_query) or 0
    if sort_by == "price_asc":
        query = query.order_by(Dish.price.asc(), Dish.id.desc())
    elif sort_by == "price_desc":
        query = query.order_by(Dish.price.desc(), Dish.id.desc())
    elif sort_by == "newest":
        query = query.order_by(Dish.created_at.desc(), Dish.id.desc())
    else:
        query = query.order_by(Dish.id.desc())

    dishes = db.scalars(
        query.offset((page_number - 1) * result_page_size).limit(result_page_size)
    ).all()
    return MenuDishListResponse(
        items=[DishResponse.model_validate(_dish_response(dish)) for dish in dishes],
        total=total,
        page=page_number,
        page_size=result_page_size,
    )


@router.get("/items", response_model=list[DishResponse], name="get_menu_items")
def get_menu_items(
    category_id: int | None = Query(default=None, ge=1),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Liệt kê món dạng cũ, dùng bởi các client không cần phân trang."""
    query = _visible_dish_query()
    if category_id is not None:
        query = query.where(Dish.category_id == category_id)
    if q and q.strip():
        query = query.where(Dish.name.contains(q.strip()))
    return [
        _dish_response(dish)
        for dish in db.scalars(query.order_by(Dish.id.asc())).all()
    ]


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
