from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.crud import crud_menu
from app.services import menu_service
from app.schemas.menu import (
    CustomerMenuOverviewOut,
    MenuCategoryBriefOut,
    MenuDishDetailOut,
    MenuDishOut,
)

router = APIRouter(prefix="/menu", tags=["Menu"])


@router.get("", response_model=CustomerMenuOverviewOut)
@router.get("/overview", response_model=CustomerMenuOverviewOut)
def get_menu_overview(db: Session = Depends(get_db)):
    return menu_service.get_customer_menu_overview(db)


@router.get("/categories", response_model=List[MenuCategoryBriefOut])
def get_menu_categories(db: Session = Depends(get_db)):
    return crud_menu.get_active_categories(db)


@router.get("/dishes", response_model=List[MenuDishOut])
@router.get("/items", response_model=List[MenuDishOut])
def get_menu_dishes(
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    min_price: Optional[Decimal] = Query(None, ge=0),
    max_price: Optional[Decimal] = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return crud_menu.get_available_dishes(
        db=db,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        skip=skip,
        limit=limit,
    )


@router.get("/dishes/{dish_id}", response_model=MenuDishDetailOut)
@router.get("/items/{dish_id}", response_model=MenuDishDetailOut)
def get_menu_dish_detail(
    dish_id: int,
    db: Session = Depends(get_db),
):
    return menu_service.get_customer_dish_detail(db=db, dish_id=dish_id)