"""API quản lý danh mục món ăn: /api/categories"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import category as category_crud
from app.db.session import get_db
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CategorySortUpdate,
    CategoryStatusUpdate,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


def get_category_or_404(
    category_id: int,
    db: Session = Depends(get_db),
):
    category = category_crud.get_category(db, category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy danh mục id={category_id}",
        )

    return category


# Lấy danh sách danh mục
@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return category_crud.get_categories(db)


# Lấy chi tiết danh mục
@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category=Depends(get_category_or_404)):
    return category


# Thêm danh mục
@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
):
    if category_crud.check_category_name(db, data.name):
        raise HTTPException(
            status_code=409,
            detail="Tên danh mục đã tồn tại",
        )

    return category_crud.create_category(db, data)


# Sửa danh mục
@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    data: CategoryUpdate,
    category=Depends(get_category_or_404),
    db: Session = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data:
        if category_crud.check_category_name(
            db,
            update_data["name"],
            category.id,
        ):
            raise HTTPException(
                status_code=409,
                detail="Tên danh mục đã tồn tại",
            )

    return category_crud.update_category(db, category, data)


# Sắp xếp thứ tự danh mục
@router.patch(
    "/{category_id}/sort",
    response_model=CategoryResponse,
)
def sort_category(
    data: CategorySortUpdate,
    category=Depends(get_category_or_404),
    db: Session = Depends(get_db),
):
    return category_crud.update_category_sort(
        db,
        category,
        data.sort_order,
    )


# Ẩn hoặc hiện danh mục
@router.patch(
    "/{category_id}/status",
    response_model=CategoryResponse,
)
def change_category_status(
    data: CategoryStatusUpdate,
    category=Depends(get_category_or_404),
    db: Session = Depends(get_db),
):
    return category_crud.update_category_status(
        db,
        category,
        data.is_active,
    )


# Xóa danh mục
@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_category(
    category=Depends(get_category_or_404),
    db: Session = Depends(get_db),
):
    if category_crud.has_dishes(db, category.id):
        raise HTTPException(
            status_code=409,
            detail="Không thể xóa danh mục vì vẫn còn món ăn thuộc danh mục này",
        )

    category_crud.delete_category(db, category)
