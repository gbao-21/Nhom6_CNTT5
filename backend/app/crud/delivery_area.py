"""CRUD cho bảng delivery_areas."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.delivery_area import DeliveryArea
from app.schemas.delivery_area import DeliveryAreaCreate, DeliveryAreaUpdate


def get_delivery_areas(db: Session) -> list[DeliveryArea]:
    return list(db.scalars(select(DeliveryArea).order_by(DeliveryArea.id.asc())))


def get_delivery_area(db: Session, area_id: int) -> DeliveryArea | None:
    return db.get(DeliveryArea, area_id)


def create_delivery_area(db: Session, data: DeliveryAreaCreate) -> DeliveryArea:
    area = DeliveryArea(**data.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def update_delivery_area(
    db: Session,
    area: DeliveryArea,
    data: DeliveryAreaUpdate,
) -> DeliveryArea:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(area, field, value)
    db.commit()
    db.refresh(area)
    return area


def delete_delivery_area(db: Session, area: DeliveryArea) -> None:
    db.delete(area)
    db.commit()

