"""API quản lý người dùng: /api/users"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import user as user_crud
from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_or_404(user_id: int, db: Session = Depends(get_db)):
    user = user_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy user id={user_id}")
    return user


@router.get("", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return user_crud.get_users(db)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user=Depends(get_user_or_404)):
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    if user_crud.get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")
    return user_crud.create_user(db, data)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    data: UserUpdate,
    user=Depends(get_user_or_404),
    db: Session = Depends(get_db),
):
    return user_crud.update_user(db, user, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user=Depends(get_user_or_404), db: Session = Depends(get_db)):
    user_crud.delete_user(db, user)

