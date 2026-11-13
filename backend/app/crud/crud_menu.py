from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import or_, text
from sqlalchemy.orm import Session, joinedload
from app.models.category import Category
from app.models.dish import Dish


def get_active_categories(db: Session) -> List[Category]:
    return (
        db.query(Category)
        .filter(Category.is_active.is_(True))
        .order_by(Category.id.asc())
        .all()
    )


def _get_sold_count_map(db: Session) -> dict[int, int]:
    try:
        rows = db.execute(
            text(
                "SELECT dish_id, COALESCE(SUM(quantity), 0) AS total_sold "
                "FROM order_items WHERE dish_id IS NOT NULL GROUP BY dish_id"
            )
        ).fetchall()
        return {int(row[0]): int(row[1]) for row in rows if row[0] is not None}
    except Exception:
        return {}


def _enrich_dish_data(dish: Dish, sold_map: dict[int, int]) -> Dish:
    setattr(dish, "sold_count", int(sold_map.get(dish.id, getattr(dish, "sold_count", 0) or 0)))
    setattr(dish, "rating", float(getattr(dish, "rating", 5.0) or 5.0))
    return dish


def search_and_filter_dishes(
    db: Session,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    is_available: Optional[bool] = True,
    sort_by: Optional[str] = None,
    page: int = 1,
    page_size: int = 12,
) -> Tuple[List[Dish], int]:
    query = (
        db.query(Dish)
        .options(joinedload(Dish.options), joinedload(Dish.category))
        .outerjoin(Category, Dish.category_id == Category.id)
        .filter(or_(Dish.category_id.is_(None), Category.is_active.is_(True)))
    )

    if is_available is not None:
        query = query.filter(Dish.is_available.is_(is_available))

    if category_id is not None:
        query = query.filter(Dish.category_id == category_id)

    if search and search.strip():
        keyword = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Dish.name.ilike(keyword),
                Dish.description.ilike(keyword),
            )
        )

    if min_price is not None:
        query = query.filter(Dish.price >= min_price)
    if max_price is not None:
        query = query.filter(Dish.price <= max_price)

    dishes = query.all()
    sold_map = _get_sold_count_map(db)

    for dish in dishes:
        _enrich_dish_data(dish, sold_map)

    sort_key = (sort_by or "").strip().lower()
    if sort_key == "price_asc":
        dishes.sort(key=lambda x: (x.price, x.id))
    elif sort_key == "price_desc":
        dishes.sort(key=lambda x: (x.price, -x.id), reverse=True)
    elif sort_key == "bestseller":
        dishes.sort(key=lambda x: (x.sold_count, x.id), reverse=True)
    elif sort_key == "rating":
        dishes.sort(key=lambda x: (x.rating, x.sold_count, x.id), reverse=True)
    elif sort_key == "newest":
        dishes.sort(key=lambda x: x.id, reverse=True)
    else:
        dishes.sort(key=lambda x: x.id)

    total = len(dishes)
    start = (page - 1) * page_size
    end = start + page_size
    return dishes[start:end], total


def get_available_dishes(
    db: Session,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Dish]:
    page = (skip // limit) + 1 if limit > 0 else 1
    items, _ = search_and_filter_dishes(
        db=db,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        is_available=True,
        page=page,
        page_size=limit,
    )
    return items


def get_available_dish_by_id(db: Session, dish_id: int) -> Optional[Dish]:
    dish = (
        db.query(Dish)
        .options(joinedload(Dish.category), joinedload(Dish.options))
        .outerjoin(Category, Dish.category_id == Category.id)
        .filter(
            Dish.id == dish_id,
            or_(Dish.category_id.is_(None), Category.is_active.is_(True)),
        )
        .first()
    )
    if not dish:
        return None

    sold_map = _get_sold_count_map(db)
    return _enrich_dish_data(dish, sold_map)