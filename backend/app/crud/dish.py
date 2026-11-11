"""CRUD cho bảng dishes và dish_options."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dish import Dish, DishOption
from app.schemas.dish import DishCreate, DishUpdate


def get_dishes(
    db: Session,
    category_id: int | None = None,
    keyword: str | None = None,
) -> list[Dish]:
    query = select(Dish).order_by(Dish.id.desc())
    if category_id is not None:
        query = query.where(Dish.category_id == category_id)
    if keyword:
        query = query.where(Dish.name.contains(keyword))
    return list(db.scalars(query))


def get_dish(db: Session, dish_id: int) -> Dish | None:
    return db.get(Dish, dish_id)


def create_dish(db: Session, data: DishCreate) -> Dish:
    payload = data.model_dump()
    options_data = payload.pop("options", [])
    dish = Dish(**payload)
    for opt in options_data:
        dish.options.append(DishOption(**opt))
    db.add(dish)
    db.commit()
    db.refresh(dish)
    return dish


def update_dish(db: Session, dish: Dish, data: DishUpdate) -> Dish:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dish, field, value)
    db.commit()
    db.refresh(dish)
    return dish


def delete_dish(db: Session, dish: Dish) -> None:
    db.delete(dish)
    db.commit()

