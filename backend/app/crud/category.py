"""CRUD cho bảng categories."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.dish import Dish
from app.schemas.category import CategoryCreate, CategoryUpdate


def get_categories(db: Session) -> list[Category]:
    statement = select(Category).order_by(
        Category.sort_order.asc(),
        Category.id.asc(),
    )
    return list(db.scalars(statement))


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def check_category_name(
    db: Session,
    name: str,
    category_id: int | None = None,
) -> bool:
    statement = select(Category).where(Category.name == name)

    if category_id is not None:
        statement = statement.where(Category.id != category_id)

    return db.scalar(statement) is not None


def has_dishes(db: Session, category_id: int) -> bool:
    statement = select(Dish.id).where(Dish.category_id == category_id)
    return db.scalar(statement) is not None


def create_category(db: Session, data: CategoryCreate) -> Category:
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    category: Category,
    data: CategoryUpdate,
) -> Category:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


def update_category_sort(
    db: Session,
    category: Category,
    sort_order: int,
) -> Category:
    category.sort_order = sort_order
    db.commit()
    db.refresh(category)
    return category


def update_category_status(
    db: Session,
    category: Category,
    is_active: bool,
) -> Category:
    category.is_active = is_active
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()
