"""CRUD cho bảng dishes và dish_options."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from app.models.order import Order, OrderItem
from app.models.dish import Dish, DishOption
from app.models.order import OrderItem
from app.schemas.dish import (
    DishCreate,
    DishUpdate,
    DishOptionCreate,
    DishOptionUpdate,
)

# =========================
# CRUD DISH
# =========================

def get_dishes(
    db: Session,
    category_id: int | None = None,
    keyword: str | None = None,
    status: str | None = None,
) -> list[Dish]:
    query = select(Dish).order_by(Dish.id.desc())

    if category_id is not None:
        query = query.where(Dish.category_id == category_id)

    if keyword:
        query = query.where(Dish.name.contains(keyword))

    if status:
        query = query.where(Dish.status == status)

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


def update_dish(
    db: Session,
    dish: Dish,
    data: DishUpdate,
) -> Dish:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dish, field, value)

    db.commit()
    db.refresh(dish)

    return dish


def has_order_items(db: Session, dish_id: int) -> bool:
    statement = select(OrderItem.id).where(
        OrderItem.dish_id == dish_id
    )

    return db.scalar(statement) is not None


def hide_dish(db: Session, dish: Dish) -> Dish:
    dish.status = "HIDDEN"
    dish.is_active = False
    dish.is_available = False

    db.commit()
    db.refresh(dish)

    return dish


def delete_dish(db: Session, dish: Dish) -> None:
    db.delete(dish)
    db.commit()


# =========================
# CRUD DISH OPTION
# =========================

def get_dish_options(
    db: Session,
    dish_id: int,
) -> list[DishOption]:
    statement = (
        select(DishOption)
        .where(DishOption.dish_id == dish_id)
        .order_by(DishOption.id.asc())
    )

    return list(db.scalars(statement))


def get_dish_option(
    db: Session,
    option_id: int,
    dish_id: int,
) -> DishOption | None:
    statement = select(DishOption).where(
        DishOption.id == option_id,
        DishOption.dish_id == dish_id,
    )

    return db.scalar(statement)

def check_option_group(
    db: Session,
    dish_id: int,
    data: DishOptionCreate,
) -> bool:
    statement = select(DishOption).where(
        DishOption.dish_id == dish_id,
        DishOption.group_name == data.group_name,
    )

    options = list(db.scalars(statement))

    for option in options:
        if (
            option.is_required != data.is_required
            or option.allow_multiple != data.allow_multiple
        ):
            return False

    return True


def create_dish_option(
    db: Session,
    dish_id: int,
    data: DishOptionCreate,
) -> DishOption:
    option = DishOption(
        dish_id=dish_id,
        **data.model_dump(),
    )

    db.add(option)
    db.commit()
    db.refresh(option)

    return option



def update_dish_option(
    db: Session,
    option: DishOption,
    data: DishOptionUpdate,
) -> DishOption:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(option, field, value)

    db.commit()
    db.refresh(option)

    return option


def delete_dish_option(
    db: Session,
    option: DishOption,
) -> None:
    db.delete(option)
    db.commit()

# =========================
# BÁO HẾT MÓN / BÁN LẠI
# =========================

def update_dish_availability(
    db: Session,
    dish: Dish,
    is_available: bool,
) -> Dish:
    if dish.status == "HIDDEN" or not dish.is_active:
        raise ValueError("Món đang bị ẩn, không thể bật bán.")

    if is_available:
        dish.status = "AVAILABLE"
        dish.is_available = True
    else:
        dish.status = "OUT_OF_STOCK"
        dish.is_available = False

    db.commit()
    db.refresh(dish)

    return dish


# =========================
# BẬT / TẮT MÓN NỔI BẬT
# =========================

def update_dish_featured(
    db: Session,
    dish: Dish,
    is_featured: bool,
) -> Dish:
    dish.is_featured = is_featured

    db.commit()
    db.refresh(dish)

    return dish


# =========================
# DANH SÁCH MÓN BÁN CHẠY
# =========================

def get_best_selling_dishes(
    db: Session,
    limit: int = 10,
):
    statement = (
        select(
            Dish,
            func.sum(OrderItem.quantity).label("sold_quantity")
        )
        .join(OrderItem, OrderItem.dish_id == Dish.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.status == "COMPLETED",
            Dish.status != "HIDDEN",
        )
        .group_by(Dish.id)
        .order_by(desc("sold_quantity"))
        .limit(limit)
    )

    results = db.execute(statement).all()

    return [
        {
            "dish": dish,
            "sold_quantity": int(sold_quantity),
        }
        for dish, sold_quantity in results
    ]
