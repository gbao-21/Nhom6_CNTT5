"""CRUD và các hàm xử lý dữ liệu giỏ hàng (carts & cart_items)."""
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.models.dish import Dish
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartOption


def normalize_note(note: str | None) -> str | None:
    """Chuẩn hóa ghi chú khi lưu: cắt khoảng trắng thừa ở 2 đầu và gộp khoảng trắng kép; chuỗi rỗng quy về None."""
    if note is None:
        return None
    cleaned = " ".join(note.strip().split())
    return cleaned if cleaned else None


def note_comparison_key(note: str | None) -> str | None:
    """Khóa so sánh ghi chú không phân biệt chữ hoa/thường ('Thêm trứng' == 'thêm trứng')."""
    normalized = normalize_note(note)
    return normalized.casefold() if normalized is not None else None


def normalize_selected_options(
    options: list[CartOption] | list[dict[str, Any]] | None,
) -> list[dict[str, int]]:
    """Chuẩn hóa danh sách tùy chọn: khử trùng lặp và sắp xếp tăng dần theo option_id.

    Nhờ đó [{"option_id": 2}, {"option_id": 1}] và [{"option_id": 1}, {"option_id": 2}]
    được nhận diện là trùng hoàn toàn mà không cần tạo sẵn option trong DB.
    """
    if not options:
        return []

    option_ids: set[int] = set()
    for opt in options:
        if isinstance(opt, CartOption):
            option_ids.add(opt.option_id)
        elif isinstance(opt, dict) and "option_id" in opt:
            option_ids.add(int(opt["option_id"]))

    return [{"option_id": oid} for oid in sorted(option_ids)]


def is_same_cart_line(
    item: CartItem,
    dish_id: int,
    normalized_options: list[dict[str, int]],
    normalized_note: str | None,
) -> bool:
    """Kiểm tra 1 dòng trong giỏ có trùng hoàn toàn (món + tùy chọn + ghi chú không phân biệt hoa/thường) hay không."""
    return (
        item.dish_id == dish_id
        and normalize_selected_options(item.selected_options) == normalized_options
        and note_comparison_key(item.note) == note_comparison_key(normalized_note)
    )


def validate_dish_available(db: Session, dish_id: int) -> Dish:
    """Chặn món không tồn tại, món đã hết hàng hoặc đang bị ẩn."""
    dish = db.get(Dish, dish_id)
    if dish is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy món ăn id={dish_id}",
        )

    dish_status = (getattr(dish, "status", "AVAILABLE") or "AVAILABLE").upper()
    is_active = getattr(dish, "is_active", True)
    is_available = getattr(dish, "is_available", True)

    if not is_active or dish_status in ("HIDDEN", "INACTIVE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Món ăn '{dish.name}' hiện đang bị ẩn, không thể thêm vào giỏ hàng",
        )

    if not is_available or dish_status in ("OUT_OF_STOCK", "UNAVAILABLE", "SOLD_OUT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Món ăn '{dish.name}' hiện đã hết hàng, không thể thêm vào giỏ hàng",
        )

    return dish


def ensure_user_exists(db: Session, user_id: int) -> None:
    """Đảm bảo user_id tồn tại trong bảng users trước khi tạo giỏ hàng."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người dùng id={user_id}",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản người dùng đã bị khóa",
        )


def get_or_create_cart_by_user(db: Session, user_id: int) -> Cart:
    """Lấy giỏ hàng của user; nếu chưa có thì kiểm tra user và khởi tạo giỏ mới."""
    cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        ensure_user_exists(db, user_id)
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def get_cart_item(db: Session, cart_item_id: int) -> CartItem | None:
    return db.get(CartItem, cart_item_id)


def verify_cart_item_ownership(cart_item: CartItem, current_user_id: int) -> None:
    """Đảm bảo người dùng chỉ được thao tác trên giỏ hàng của chính mình."""
    if cart_item.cart is None or cart_item.cart.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chỉ được phép thao tác trên giỏ hàng của mình",
        )


def add_item_to_user_cart(
    db: Session,
    current_user_id: int,
    data: CartItemCreate,
) -> CartItem:
    """Thêm món vào giỏ của user hiện tại:
    - Chặn món hết/ẩn.
    - Trùng hoàn toàn (cùng món + cùng tùy chọn + cùng ghi chú) -> cộng dồn số lượng.
    - Cùng món nhưng khác tùy chọn hoặc khác ghi chú -> tạo dòng riêng.
    """
    normalized_options = normalize_selected_options(data.selected_options)
    normalized_note = normalize_note(data.note)

    # 1. Chặn món hết / ẩn
    validate_dish_available(db, data.dish_id)

    # 2. Lấy giỏ hàng của chính mình
    cart = get_or_create_cart_by_user(db, current_user_id)

    # 3. Kiểm tra trùng hoàn toàn trong giỏ hàng -> cộng dồn
    for existing_item in cart.items:
        if is_same_cart_line(
            existing_item,
            dish_id=data.dish_id,
            normalized_options=normalized_options,
            normalized_note=normalized_note,
        ):
            existing_item.quantity += data.quantity
            existing_item.selected_options = normalized_options
            existing_item.note = normalized_note
            db.commit()
            db.refresh(existing_item)
            return existing_item

    # 4. Khác món hoặc khác tùy chọn / ghi chú -> thêm dòng riêng
    new_item = CartItem(
        cart_id=cart.id,
        dish_id=data.dish_id,
        selected_options=normalized_options,
        note=normalized_note,
        quantity=data.quantity,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


def update_user_cart_item(
    db: Session,
    current_user_id: int,
    cart_item_id: int,
    data: CartItemUpdate,
) -> CartItem:
    """Sửa dòng trong giỏ hàng của mình:
    - Chỉ cho phép sửa nếu dòng đó thuộc giỏ của current_user_id.
    - Chặn nếu món ăn bị hết hoặc ẩn.
    - Nếu sau khi đổi tùy chọn/ghi chú mà trùng hoàn toàn với 1 dòng khác trong giỏ -> cộng dồn vào dòng đó.
    """
    cart_item = get_cart_item(db, cart_item_id)
    if cart_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy món trong giỏ id={cart_item_id}",
        )

    # 1. Chỉ thao tác trên giỏ của mình
    verify_cart_item_ownership(cart_item, current_user_id)

    fields_set = data.model_fields_set

    # 2. Xác định tùy chọn, ghi chú, số lượng mới
    if "selected_options" in fields_set and data.selected_options is not None:
        target_options = normalize_selected_options(data.selected_options)
    else:
        target_options = normalize_selected_options(cart_item.selected_options)

    if "note" in fields_set:
        target_note = normalize_note(data.note)
    else:
        target_note = normalize_note(cart_item.note)

    if "quantity" in fields_set and data.quantity is not None:
        target_quantity = data.quantity
    else:
        target_quantity = cart_item.quantity

    # 3. Chặn nếu món ăn đã hết / ẩn
    validate_dish_available(db, cart_item.dish_id)

    # 4. Nếu sau khi sửa tùy chọn/ghi chú mà trùng hoàn toàn với 1 dòng khác trong cùng giỏ -> cộng dồn
    for other_item in cart_item.cart.items:
        if other_item.id != cart_item.id and is_same_cart_line(
            other_item,
            dish_id=cart_item.dish_id,
            normalized_options=target_options,
            normalized_note=target_note,
        ):
            other_item.quantity += target_quantity
            other_item.selected_options = target_options
            other_item.note = target_note
            db.delete(cart_item)
            db.commit()
            db.refresh(other_item)
            return other_item

    # 5. Cập nhật dòng hiện tại
    cart_item.selected_options = target_options
    cart_item.note = target_note
    cart_item.quantity = target_quantity
    db.commit()
    db.refresh(cart_item)
    return cart_item


def delete_user_cart_item(
    db: Session,
    current_user_id: int,
    cart_item_id: int,
) -> None:
    """Xoá 1 dòng khỏi giỏ hàng (chỉ xoá được trên giỏ của chính mình)."""
    cart_item = get_cart_item(db, cart_item_id)
    if cart_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy món trong giỏ id={cart_item_id}",
        )

    verify_cart_item_ownership(cart_item, current_user_id)

    db.delete(cart_item)
    db.commit()


def clear_user_cart(db: Session, current_user_id: int) -> None:
    """Xoá toàn bộ món trong giỏ hàng của chính mình."""
    cart = db.scalar(select(Cart).where(Cart.user_id == current_user_id))
    if cart is None:
        return
    for item in list(cart.items):
        db.delete(item)
    db.commit()
