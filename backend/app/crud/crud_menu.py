from decimal import Decimal
from typing import List, Optional
from sqlalchemy import or_
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


def get_available_dishes(
    db: Session,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Dish]:
    query = (
        db.query(Dish)
        .options(joinedload(Dish.options), joinedload(Dish.category))
        .outerjoin(Category, Dish.category_id == Category.id)
        .filter(
            Dish.is_available.is_(True),
            or_(Dish.category_id.is_(None), Category.is_active.is_(True)),
        )
    )

    if category_id is not None:
        query = query.filter(Dish.category_id == category_id)

    if search:
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

    dishes = query.order_by(Dish.id.asc()).offset(skip).limit(limit).all()
    for dish in dishes:
        dish.options = [opt for opt in dish.options if opt.is_available]
    return dishes


def get_available_dish_by_id(db: Session, dish_id: int) -> Optional[Dish]:
    dish = (
        db.query(Dish)
        .options(joinedload(Dish.category), joinedload(Dish.options))
        .outerjoin(Category, Dish.category_id == Category.id)
        .filter(
            Dish.id == dish_id,
            Dish.is_available.is_(True),
            or_(Dish.category_id.is_(None), Category.is_active.is_(True)),
        )
        .first()
    )
    if dish:
        dish.options = [opt for opt in dish.options if opt.is_available]
    return dish