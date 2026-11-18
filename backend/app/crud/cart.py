"""CRUD và các hàm xử lý dữ liệu giỏ hàng & tính tiền ở server (carts & cart_items)."""
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.user import get_shipping_fee_by_area
from app.models.cart import Cart, CartItem
from app.models.dish import Dish, DishOption
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartOption
from app.services.promotion_service import calculate_discount


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


def extract_sorted_option_ids(
    options: list[CartOption] | list[dict[str, Any]] | None,
) -> list[int]:
    """Trích xuất danh sách option_id đã khử trùng và sắp xếp tăng dần."""
    if not options:
        return []
    option_ids: set[int] = set()
    for opt in options:
        if isinstance(opt, CartOption):
            option_ids.add(opt.option_id)
        elif isinstance(opt, dict) and "option_id" in opt:
            option_ids.add(int(opt["option_id"]))
    return sorted(option_ids)


def normalize_selected_options(
    options: list[CartOption] | list[dict[str, Any]] | None,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    """Chuẩn hóa danh sách tùy chọn: khử trùng lặp và sắp xếp tăng dần theo option_id.
    Nếu có truyền name/price hoặc tìm thấy trong bảng dish_options thì lưu kèm để đối chiếu đổi giá.
    """
    if not options:
        return []

    by_id: dict[int, dict[str, Any]] = {}
    for opt in options:
        if isinstance(opt, CartOption):
            oid = opt.option_id
            raw_name = opt.name
            raw_price = opt.price
        elif isinstance(opt, dict) and "option_id" in opt:
            oid = int(opt["option_id"])
            raw_name = opt.get("name")
            raw_price = opt.get("price", 0)
        else:
            continue

        entry: dict[str, Any] = {"option_id": oid}
        if db is not None:
            db_opt = db.get(DishOption, oid)
            if db_opt is not None:
                entry["name"] = db_opt.name
                entry["price"] = float(db_opt.price)
            else:
                if raw_name is not None:
                    entry["name"] = raw_name
                entry["price"] = float(raw_price or 0)
        else:
            if raw_name is not None:
                entry["name"] = raw_name
            if raw_price is not None:
                entry["price"] = float(raw_price)

        by_id[oid] = entry

    return [by_id[oid] for oid in sorted(by_id.keys())]


def is_same_cart_line(
    item: CartItem,
    dish_id: int,
    normalized_options: list[dict[str, Any]],
    normalized_note: str | None,
) -> bool:
    """Kiểm tra 1 dòng trong giỏ có trùng hoàn toàn (món + tùy chọn + ghi chú không phân biệt hoa/thường) hay không."""
    return (
        item.dish_id == dish_id
        and extract_sorted_option_ids(item.selected_options)
        == extract_sorted_option_ids(normalized_options)
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


def enrich_cart_item(db: Session, item: CartItem) -> CartItem:
    """Tính tiền từng dòng ở server (giá món + tùy chọn) và phát hiện món hết / đổi giá."""
    dish = getattr(item, "dish", None) or db.get(Dish, item.dish_id)
    item_warnings: list[str] = []
    is_available = True
    is_price_changed = False

    if dish is None:
        item.dish_name = f"Món ăn #{item.dish_id} (Không còn tồn tại)"
        item.dish_image_url = None
        current_dish_price = Decimal(str(item.dish_price_snapshot or 0))
        old_price = float(current_dish_price)
        is_available = False
        item_warnings.append(f"Món ăn id={item.dish_id} không còn tồn tại trên hệ thống")
    else:
        item.dish_name = dish.name
        item.dish_image_url = dish.image_url
        current_dish_price = Decimal(str(dish.price or 0))

        # Kiểm tra món hết hàng hoặc bị ẩn
        dish_status = (getattr(dish, "status", "AVAILABLE") or "AVAILABLE").upper()
        if not getattr(dish, "is_active", True) or dish_status in ("HIDDEN", "INACTIVE"):
            is_available = False
            item_warnings.append(f"Món '{dish.name}' hiện đang bị ẩn hoặc ngừng phục vụ")
        elif not getattr(dish, "is_available", True) or dish_status in (
            "OUT_OF_STOCK",
            "UNAVAILABLE",
            "SOLD_OUT",
        ):
            is_available = False
            item_warnings.append(f"Món '{dish.name}' hiện đã hết hàng")

        # Kiểm tra món đổi giá so với lúc thêm vào giỏ
        if item.dish_price_snapshot is not None:
            snapshot_price = Decimal(str(item.dish_price_snapshot))
            old_price = float(snapshot_price)
            if snapshot_price != current_dish_price:
                is_price_changed = True
                item_warnings.append(
                    f"Món '{dish.name}' đã đổi giá từ {int(snapshot_price):,}đ thành {int(current_dish_price):,}đ"
                )
        else:
            old_price = float(current_dish_price)

    # Tính tiền tùy chọn (options_price) ở server
    options_price = Decimal("0")
    detailed_options: list[dict[str, Any]] = []
    raw_options = item.selected_options or []

    # Map lại giá cũ từng option (nếu có lưu trong JSON)
    saved_opt_map: dict[int, dict[str, Any]] = {}
    for raw in raw_options:
        if isinstance(raw, dict) and "option_id" in raw:
            saved_opt_map[int(raw["option_id"])] = raw
        elif isinstance(raw, CartOption):
            saved_opt_map[raw.option_id] = raw.model_dump()

    for opt_id in sorted(saved_opt_map.keys()):
        saved_opt = saved_opt_map[opt_id]
        db_opt = db.get(DishOption, opt_id)
        if db_opt is not None:
            opt_price = Decimal(str(db_opt.price or 0))
            opt_name = db_opt.name
            if not getattr(db_opt, "is_available", True):
                is_available = False
                item_warnings.append(
                    f"Tùy chọn '{opt_name}' của món '{item.dish_name}' hiện đã hết"
                )
            if "price" in saved_opt and saved_opt["price"] is not None:
                saved_opt_price = Decimal(str(saved_opt["price"]))
                if saved_opt_price != opt_price and saved_opt_price > 0:
                    is_price_changed = True
                    item_warnings.append(
                        f"Tùy chọn '{opt_name}' đã đổi giá từ {int(saved_opt_price):,}đ thành {int(opt_price):,}đ"
                    )
        else:
            opt_price = Decimal(str(saved_opt.get("price") or 0))
            opt_name = saved_opt.get("name")

        options_price += opt_price
        detailed_options.append(
            {
                "option_id": opt_id,
                "name": opt_name,
                "price": float(opt_price),
            }
        )

    unit_price = current_dish_price + options_price
    line_total = unit_price * item.quantity

    item.old_price = old_price
    item.dish_price = float(current_dish_price)
    item.options_price = float(options_price)
    item.unit_price = float(unit_price)
    item.selected_options = detailed_options
    item.line_total = float(line_total)
    item.is_available = is_available
    item.is_price_changed = is_price_changed
    item.warnings = item_warnings
    return item


def calculate_cart_summary(
    db: Session,
    cart: Cart,
    delivery_area_id: int | None = None,
    voucher_code: str | None = None,
) -> Cart:
    """Tính toán toàn bộ giỏ hàng ở server:
    - Thành tiền từng dòng (giá món + tùy chọn) * số lượng
    - Tạm tính (subtotal)
    - Phí ship theo khu vực (hàm get_shipping_fee_by_area của module Tài khoản)
    - Giảm giá (hàm calculate_discount của module Khuyến mãi)
    - Tổng tiền (total_amount)
    - Cảnh báo khi có món đã hết hoặc đổi giá
    """
    subtotal = Decimal("0")
    total_qty = 0
    has_unavailable = False
    has_price_changes = False
    all_warnings: list[str] = []

    for item in cart.items:
        enrich_cart_item(db, item)
        subtotal += Decimal(str(item.line_total))
        total_qty += item.quantity
        if not item.is_available:
            has_unavailable = True
        if item.is_price_changed:
            has_price_changes = True
        for w in item.warnings:
            if w not in all_warnings:
                all_warnings.append(w)

    # Tính phí ship theo khu vực (hàm của module Tài khoản)
    shipping_fee = get_shipping_fee_by_area(
        db,
        delivery_area_id=delivery_area_id,
        user_id=cart.user_id,
    )

    # Tính giảm giá (hàm của module Khuyến mãi)
    discount_amount = calculate_discount(
        db,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        voucher_code=voucher_code,
    )

    total_amount = max(Decimal("0"), subtotal + shipping_fee - discount_amount)

    cart.total_items = len(cart.items)
    cart.total_quantity = total_qty
    cart.subtotal = float(subtotal)
    cart.delivery_area_id = delivery_area_id
    cart.shipping_fee = float(shipping_fee)
    cart.voucher_code = voucher_code.strip().upper() if (voucher_code and voucher_code.strip()) else None
    cart.discount_amount = float(discount_amount)
    cart.total_amount = float(total_amount)
    cart.has_unavailable_items = has_unavailable
    cart.has_price_changes = has_price_changes
    cart.can_checkout = len(cart.items) > 0 and not has_unavailable
    cart.warnings = all_warnings
    return cart


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


def get_or_create_cart_by_user(
    db: Session,
    user_id: int,
    delivery_area_id: int | None = None,
    voucher_code: str | None = None,
) -> Cart:
    """Lấy giỏ hàng của user kèm tính tiền ở server; nếu chưa có thì khởi tạo giỏ mới."""
    cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
    if cart is None:
        ensure_user_exists(db, user_id)
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return calculate_cart_summary(
        db,
        cart,
        delivery_area_id=delivery_area_id,
        voucher_code=voucher_code,
    )


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
    - Lưu snapshot giá món lúc thêm (dish_price_snapshot) để phát hiện đổi giá về sau.
    - Trùng hoàn toàn (cùng món + cùng tùy chọn + cùng ghi chú) -> cộng dồn số lượng.
    - Cùng món nhưng khác tùy chọn hoặc khác ghi chú -> tạo dòng riêng.
    """
    # 1. Chặn món hết / ẩn
    dish = validate_dish_available(db, data.dish_id)

    normalized_options = normalize_selected_options(data.selected_options, db=db)
    normalized_note = normalize_note(data.note)

    # 2. Lấy giỏ hàng của chính mình
    cart = db.scalar(select(Cart).where(Cart.user_id == current_user_id))
    if cart is None:
        ensure_user_exists(db, current_user_id)
        cart = Cart(user_id=current_user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)

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
            if existing_item.dish_price_snapshot is None:
                existing_item.dish_price_snapshot = dish.price
            db.commit()
            db.refresh(existing_item)
            return enrich_cart_item(db, existing_item)

    # 4. Khác món hoặc khác tùy chọn / ghi chú -> thêm dòng riêng
    new_item = CartItem(
        cart_id=cart.id,
        dish_id=data.dish_id,
        dish_price_snapshot=dish.price,
        selected_options=normalized_options,
        note=normalized_note,
        quantity=data.quantity,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return enrich_cart_item(db, new_item)


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
        target_options = normalize_selected_options(data.selected_options, db=db)
    else:
        target_options = normalize_selected_options(cart_item.selected_options, db=db)

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
            return enrich_cart_item(db, other_item)

    # 5. Cập nhật dòng hiện tại
    cart_item.selected_options = target_options
    cart_item.note = target_note
    cart_item.quantity = target_quantity
    db.commit()
    db.refresh(cart_item)
    return enrich_cart_item(db, cart_item)


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
