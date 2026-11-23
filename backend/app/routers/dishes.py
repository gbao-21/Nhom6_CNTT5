"""API quản lý món ăn: /api/dishes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import dish as dish_crud
from app.db.session import get_db
from app.schemas.dish import (
    DishCreate,
    DishResponse,
    DishUpdate,
    DishOptionCreate,
    DishOptionUpdate,
    DishOptionResponse,
    DishAvailabilityUpdate,
    DishFeaturedUpdate,
    BestSellerResponse,
)

import uuid
from pathlib import Path
from fastapi import UploadFile, File

router = APIRouter(prefix="/dishes", tags=["Dishes"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "dishes"

MAX_FILE_SIZE = 5 * 1024 * 1024

ALLOWED_IMAGES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

def get_dish_or_404(
    dish_id: int,
    db: Session = Depends(get_db),
):
    dish = dish_crud.get_dish(db, dish_id)

    if dish is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy món ăn id={dish_id}",
        )

    return dish


def get_option_or_404(
    dish_id: int,
    option_id: int,
    db: Session = Depends(get_db),
):
    option = dish_crud.get_dish_option(db, option_id, dish_id)

    if option is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tùy chọn của món ăn này",
        )

    return option


# Danh sách món ăn
@router.get("", response_model=list[DishResponse])
def list_dishes(
    category_id: int | None = None,
    q: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    return dish_crud.get_dishes(
        db,
        category_id=category_id,
        keyword=q,
        status=status,
    )

# =========================
# DANH SÁCH MÓN BÁN CHẠY
# =========================

@router.get("/best-sellers", response_model=list[BestSellerResponse])
def list_best_selling_dishes(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit phải từ 1 đến 100",
        )

    return dish_crud.get_best_selling_dishes(db, limit)

# Chi tiết món ăn
@router.get("/{dish_id}", response_model=DishResponse)
def get_dish(dish=Depends(get_dish_or_404)):
    return dish


# Thêm món ăn
@router.post(
    "",
    response_model=DishResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dish(
    data: DishCreate,
    db: Session = Depends(get_db),
):
    return dish_crud.create_dish(db, data)


# Sửa món ăn
@router.put("/{dish_id}", response_model=DishResponse)
def update_dish(
    data: DishUpdate,
    dish=Depends(get_dish_or_404),
    db: Session = Depends(get_db),
):
    return dish_crud.update_dish(db, dish, data)


# Ẩn món ăn
@router.patch("/{dish_id}/hide", response_model=DishResponse)
def hide_dish(
    dish=Depends(get_dish_or_404),
    db: Session = Depends(get_db),
):
    return dish_crud.hide_dish(db, dish)


# Xóa món ăn
@router.delete(
    "/{dish_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_dish(
    dish=Depends(get_dish_or_404),
    db: Session = Depends(get_db),
):
    if dish_crud.has_order_items(db, dish.id):
        raise HTTPException(
            status_code=409,
            detail="Món ăn đã có trong đơn hàng. Chỉ được phép ẩn món, không được xóa.",
        )

    dish_crud.delete_dish(db, dish)


# =========================
# DISH OPTIONS
# =========================

# Danh sách tùy chọn
@router.get(
    "/{dish_id}/options",
    response_model=list[DishOptionResponse],
)
def list_dish_options(
    dish=Depends(get_dish_or_404),
    db: Session = Depends(get_db),
):
    return dish_crud.get_dish_options(db, dish.id)


# Thêm tùy chọn

@router.post(
    "/{dish_id}/options",
    response_model=DishOptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dish_option(
    data: DishOptionCreate,
    dish=Depends(get_dish_or_404),
    db: Session = Depends(get_db),
):
    if not dish_crud.check_option_group(db, dish.id, data):
        raise HTTPException(
            status_code=400,
            detail="Các tùy chọn trong cùng nhóm phải có cấu hình giống nhau",
        )

    return dish_crud.create_dish_option(db, dish.id, data)



# Sửa tùy chọn
@router.put(
    "/{dish_id}/options/{option_id}",
    response_model=DishOptionResponse,
)
def update_dish_option(
    data: DishOptionUpdate,
    option=Depends(get_option_or_404),
    db: Session = Depends(get_db),
):
    return dish_crud.update_dish_option(db, option, data)


# Xóa tùy chọn
@router.delete(
    "/{dish_id}/options/{option_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_dish_option(
    option=Depends(get_option_or_404),
    db: Session = Depends(get_db),
):
    dish_crud.delete_dish_option(db, option)

# Upload ảnh món ăn
@router.post("/{dish_id}/image", response_model=DishResponse)
async def upload_dish_image(
    file: UploadFile = File(...),
    dish=Depends(get_dish_or_404),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGES:
        raise HTTPException(
            status_code=400,
            detail="Chỉ chấp nhận ảnh JPG, PNG hoặc WEBP",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Dung lượng ảnh không được vượt quá 5MB",
        )

    # Kiểm tra chữ ký file ảnh thực tế
    valid_image = False

    if file.content_type == "image/jpeg":
        valid_image = content.startswith(b"\xff\xd8\xff")

    elif file.content_type == "image/png":
        valid_image = content.startswith(b"\x89PNG\r\n\x1a\n")

    elif file.content_type == "image/webp":
        valid_image = (
            content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        )

    if not valid_image:
        raise HTTPException(
            status_code=400,
            detail="File tải lên không phải ảnh hợp lệ",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    extension = ALLOWED_IMAGES[file.content_type]
    filename = f"{uuid.uuid4().hex}{extension}"

    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(content)

    dish.image_url = f"/uploads/dishes/{filename}"

    db.commit()
    db.refresh(dish)

    return dish

# =========================
# BÁO HẾT MÓN / BÁN LẠI
# =========================

@router.patch("/{dish_id}/availability", response_model=DishResponse)
def update_dish_availability(
    data: DishAvailabilityUpdate,
    dish=Depends(get_dish_or_404),
    db: Session = Depends(get_db),
):
    try:
        return dish_crud.update_dish_availability(
            db,
            dish,
            data.is_available,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# =========================
# BẬT / TẮT MÓN NỔI BẬT
# =========================

@router.patch("/{dish_id}/featured", response_model=DishResponse)
def update_dish_featured(
    data: DishFeaturedUpdate,
    dish=Depends(get_dish_or_404),
    db: Session = Depends(get_db),
):
    return dish_crud.update_dish_featured(
        db,
        dish,
        data.is_featured,
    )
