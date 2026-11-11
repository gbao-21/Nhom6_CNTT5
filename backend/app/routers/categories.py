"""API quản lý danh mục món ăn: /api/categories"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import category as category_crud
from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


def get_category_or_404(category_id: int, db: Session = Depends(get_db)):
    category = category_crud.get_category(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy danh mục id={category_id}",
        )
    return category


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return category_crud.get_categories(db)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category=Depends(get_category_or_404)):
    return category


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    return category_crud.create_category(db, data)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    data: CategoryUpdate,
    category=Depends(get_category_or_404),
    db: Session = Depends(get_db),
):
    return category_crud.update_category(db, category, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category=Depends(get_category_or_404),
    db: Session = Depends(get_db),
):
    category_crud.delete_category(db, category)

