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

router = APIRouter(prefix="/menu", tags=["Menu"])


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
