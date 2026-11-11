"""API quản lý khu vực giao hàng: /api/delivery-areas"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import delivery_area as area_crud
from app.db.session import get_db
from app.schemas.delivery_area import (
    DeliveryAreaCreate,
    DeliveryAreaResponse,
    DeliveryAreaUpdate,
)

router = APIRouter(prefix="/delivery-areas", tags=["Delivery Areas"])


def get_area_or_404(area_id: int, db: Session = Depends(get_db)):
    area = area_crud.get_delivery_area(db, area_id)
    if area is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy khu vực giao hàng id={area_id}",
        )
    return area


@router.get("", response_model=list[DeliveryAreaResponse])
def list_delivery_areas(db: Session = Depends(get_db)):
    return area_crud.get_delivery_areas(db)


@router.get("/{area_id}", response_model=DeliveryAreaResponse)
def get_delivery_area(area=Depends(get_area_or_404)):
    return area


@router.post("", response_model=DeliveryAreaResponse, status_code=status.HTTP_201_CREATED)
def create_delivery_area(data: DeliveryAreaCreate, db: Session = Depends(get_db)):
    return area_crud.create_delivery_area(db, data)


@router.put("/{area_id}", response_model=DeliveryAreaResponse)
def update_delivery_area(
    data: DeliveryAreaUpdate,
    area=Depends(get_area_or_404),
    db: Session = Depends(get_db),
):
    return area_crud.update_delivery_area(db, area, data)


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_area(area=Depends(get_area_or_404), db: Session = Depends(get_db)):
    area_crud.delete_delivery_area(db, area)

