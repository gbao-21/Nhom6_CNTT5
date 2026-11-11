"""API quản lý món ăn: /api/dishes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import dish as dish_crud
from app.db.session import get_db
from app.schemas.dish import DishCreate, DishResponse, DishUpdate

router = APIRouter(prefix="/dishes", tags=["Dishes"])


def get_dish_or_404(dish_id: int, db: Session = Depends(get_db)):
    dish = dish_crud.get_dish(db, dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy món ăn id={dish_id}")
    return dish


@router.get("", response_model=list[DishResponse])
def list_dishes(
    category_id: int | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    return dish_crud.get_dishes(db, category_id=category_id, keyword=q)


@router.get("/{dish_id}", response_model=DishResponse)
def get_dish(dish=Depends(get_dish_or_404)):
    return dish


@router.post("", response_model=DishResponse, status_code=status.HTTP_201_CREATED)
def create_dish(data: DishCreate, db: Session = Depends(get_db)):
    return dish_crud.create_dish(db, data)


@router.put("/{dish_id}", response_model=DishResponse)
def update_dish(
    data: DishUpdate,
    dish=Depends(get_dish_or_404),
    db: Session = Depends(get_db),
):
    return dish_crud.update_dish(db, dish, data)


@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(dish=Depends(get_dish_or_404), db: Session = Depends(get_db)):
    dish_crud.delete_dish(db, dish)

