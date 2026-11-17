"""Service xử lý nghiệp vụ đặt hàng (Order) trong một transaction."""
from datetime import datetime, time, timedelta
from decimal import Decimal
import threading
from typing import Any
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.order_status import VALID_STATUS_TRANSITIONS, is_valid_status_transition
from app.models.cart import Cart
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish, DishOption
from app.models.order import Order, OrderItem, OrderStatusHistory
from app.models.user import User
from app.schemas.order import OrderCreate, OrderItemCreate, OrderOptionCreate

# Khóa đồng bộ theo user_id và bộ nhớ tạm lưu idempotency_key / chữ ký đơn hàng để chống bấm đặt 2 lần
_GLOBAL_LOCK = threading.Lock()
_USER_ACTIVE_ORDERS: set[int] = set()
_IDEMPOTENCY_CACHE: dict[tuple[int, str], tuple[datetime, int]] = {}
_RECENT_SUBMISSION_CACHE: dict[int, tuple[datetime, tuple, str]] = {}


def generate_order_code() -> str:
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:4].upper()
    return f"ORD-{timestamp}-{suffix}"


def _parse_hhmm(value: str) -> time:
    parts = value.strip().split(":")
    return time(hour=int(parts[0]), minute=int(parts[1]))


def validate_desired_delivery_time(desired_delivery_at: datetime | None) -> None:
    """Kiểm tra giờ giao mong muốn phải nằm trong khung giờ mở cửa của quán."""
    if desired_delivery_at is None:
        return

    open_time = _parse_hhmm(getattr(settings, "STORE_OPEN_TIME", "07:00"))
    close_time = _parse_hhmm(getattr(settings, "STORE_CLOSE_TIME", "23:00"))
    delivery_time = desired_delivery_at.time()

    if open_time <= close_time:
        is_open = open_time <= delivery_time <= close_time
    else:
        # Trường hợp mở xuyên đêm (ví dụ 18:00 -> 02:00 sáng hôm sau)
        is_open = delivery_time >= open_time or delivery_time <= close_time

    if not is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Giờ giao mong muốn ({delivery_time.strftime('%H:%M')}) nằm ngoài giờ mở cửa "
                f"({settings.STORE_OPEN_TIME} - {settings.STORE_CLOSE_TIME})"
            ),
        )


def _extract_items_from_cart(cart: Cart | None) -> list[OrderItemCreate]:
    """Chuyển các dòng trong giỏ hàng (CartItem) sang danh sách OrderItemCreate."""
    if cart is None or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giỏ hàng đang trống hoặc đơn hàng vừa được đặt, không thể đặt đơn",
        )

    result: list[OrderItemCreate] = []
    for c_item in cart.items:
        opts: list[OrderOptionCreate] = []
        for raw_opt in c_item.selected_options or []:
            if isinstance(raw_opt, dict) and "option_id" in raw_opt:
                opts.append(
                    OrderOptionCreate(
                        option_id=int(raw_opt["option_id"]),
                        name=raw_opt.get("name"),
                        price=(
                            Decimal(str(raw_opt["price"]))
                            if raw_opt.get("price") is not None
                            else None
                        ),
                    )
                )
        result.append(
            OrderItemCreate(
                dish_id=c_item.dish_id,
                selected_options=opts,
                note=c_item.note,
                quantity=c_item.quantity,
            )
        )
    return result


def _validate_and_snapshot_item(
    db: Session,
    item_in: OrderItemCreate,
) -> OrderItem:
    """Kiểm tra món còn bán và lưu snapshot tên/giá món + tùy chọn tại thời điểm đặt."""
    dish = db.get(Dish, item_in.dish_id)
    if dish is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Món ăn id={item_in.dish_id} không tồn tại",
        )

    dish_status = (getattr(dish, "status", "AVAILABLE") or "AVAILABLE").upper()
    is_active = getattr(dish, "is_active", True)
    is_available = getattr(dish, "is_available", True)

    if not is_active or dish_status in ("HIDDEN", "INACTIVE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Món ăn '{dish.name}' hiện đang bị ẩn hoặc ngừng kinh doanh, không thể đặt đơn",
        )

    if not is_available or dish_status in ("OUT_OF_STOCK", "UNAVAILABLE", "SOLD_OUT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Món ăn '{dish.name}' hiện đã hết hàng, không thể đặt đơn",
        )

    dish_price = Decimal(str(dish.price or 0))
    options_price = Decimal("0")
    selected_options_snapshot: list[dict[str, Any]] = []

    # Khử trùng và sắp xếp theo option_id để lưu chuẩn
    seen_option_ids: set[int] = set()
    sorted_opts = sorted(item_in.selected_options or [], key=lambda x: x.option_id)

    for opt_in in sorted_opts:
        if opt_in.option_id in seen_option_ids:
            continue
        seen_option_ids.add(opt_in.option_id)

        db_opt = db.get(DishOption, opt_in.option_id)
        if db_opt is not None:
            if db_opt.dish_id != dish.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tùy chọn id={opt_in.option_id} không thuộc món '{dish.name}'",
                )
            if not getattr(db_opt, "is_available", True):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tùy chọn '{db_opt.name}' của món '{dish.name}' hiện đã hết",
                )
            opt_name = db_opt.name
            opt_price = Decimal(str(db_opt.price or 0))
        else:
            # Nếu dự án truyền option JSON tự do không nằm trong bảng dish_options
            opt_name = opt_in.name or f"Tùy chọn #{opt_in.option_id}"
            opt_price = Decimal(str(opt_in.price or 0))

        options_price += opt_price
        selected_options_snapshot.append(
            {
                "option_id": opt_in.option_id,
                "name": opt_name,
                "price": float(opt_price),
            }
        )

    cleaned_note = " ".join(item_in.note.strip().split()) if (item_in.note and item_in.note.strip()) else None
    line_total = (dish_price + options_price) * item_in.quantity

    return OrderItem(
        dish_id=dish.id,
        dish_name=dish.name,
        dish_price=dish_price,
        selected_options=selected_options_snapshot,
        options_price=options_price,
        note=cleaned_note,
        quantity=item_in.quantity,
        line_total=line_total,
    )


def _build_submission_fingerprint(
    data: OrderCreate,
    subtotal: Decimal,
    total_amount: Decimal,
    order_items: list[OrderItem],
) -> tuple:
    item_sig = tuple(
        sorted(
            (
                it.dish_id,
                it.quantity,
                it.note or "",
                tuple(
                    opt["option_id"]
                    for opt in (it.selected_options or [])
                    if isinstance(opt, dict) and "option_id" in opt
                ),
            )
            for it in order_items
        )
    )
    return (
        data.recipient_phone.strip(),
        data.delivery_address.strip(),
        data.delivery_area_id,
        str(subtotal),
        str(total_amount),
        item_sig,
    )


def _check_duplicate_submission(
    db: Session,
    user_id: int,
    data: OrderCreate,
    subtotal: Decimal,
    total_amount: Decimal,
    order_items: list[OrderItem],
    idempotency_key: str | None = None,
) -> tuple:
    """Chống bấm đặt 2 lần:
    1. Kiểm tra theo idempotency_key (nếu có truyền).
    2. Kiểm tra trong khoảng thời gian ngắn (ORDER_DEDUP_WINDOW_SECONDS) xem user vừa đặt đơn giống hệt chưa.
    """
    dedup_seconds = getattr(settings, "ORDER_DEDUP_WINDOW_SECONDS", 15)
    now = datetime.now()

    if idempotency_key:
        cache_key = (user_id, idempotency_key.strip())
        cached = _IDEMPOTENCY_CACHE.get(cache_key)
        if cached is not None:
            created_time, existing_order_id = cached
            if (now - created_time).total_seconds() <= 300:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Đơn hàng đã được đặt (id={existing_order_id}), vui lòng không bấm đặt 2 lần",
                )

    fingerprint = _build_submission_fingerprint(data, subtotal, total_amount, order_items)
    recent_entry = _RECENT_SUBMISSION_CACHE.get(user_id)
    if recent_entry is not None:
        last_time, last_fp, last_code = recent_entry
        if (now - last_time).total_seconds() <= dedup_seconds and last_fp == fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Đơn hàng tương tự vừa được tạo (mã đơn {last_code}), "
                    "vui lòng không bấm đặt 2 lần"
                ),
            )

    return fingerprint


def create_order_for_user(
    db: Session,
    user_id: int,
    data: OrderCreate,
    idempotency_key: str | None = None,
) -> Order:
    """API đặt món trong 1 transaction:
    - Chống bấm đặt 2 lần (cả đồng thời lẫn bấm liên tiếp).
    - Kiểm tra giờ giao mong muốn trong giờ mở cửa.
    - Kiểm tra khu vực giao hàng & kiểm tra từng món còn bán.
    - Lưu snapshot giá món và tùy chọn tại thời điểm đặt.
    - Tạo đơn ở trạng thái Chờ xác nhận (PENDING) + chi tiết đơn + lịch sử trạng thái + xoá giỏ hàng
      trong cùng một transaction (lỗi bất kỳ bước nào sẽ rollback toàn bộ).
    """
    with _GLOBAL_LOCK:
        if user_id in _USER_ACTIVE_ORDERS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Đơn hàng của bạn đang được xử lý, vui lòng không bấm đặt 2 lần",
            )
        _USER_ACTIVE_ORDERS.add(user_id)

    try:
        # 1. Kiểm tra giờ giao mong muốn phải nằm trong giờ mở cửa
        validate_desired_delivery_time(data.desired_delivery_at)

        # 2. Kiểm tra khu vực giao hàng
        area = db.get(DeliveryArea, data.delivery_area_id)
        if area is None or not getattr(area, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Khu vực giao hàng không hợp lệ hoặc tạm ngưng phục vụ",
            )

        # 3. Lấy giỏ hàng của user (để lấy món nếu data.items trống, và để xoá giỏ sau khi tạo đơn)
        cart = db.scalar(select(Cart).where(Cart.user_id == user_id))
        items_to_order = data.items if data.items else _extract_items_from_cart(cart)

        # 4. Kiểm tra món còn bán và tạo snapshot OrderItem (lưu giá & tùy chọn lúc đặt)
        subtotal = Decimal("0")
        order_items: list[OrderItem] = []
        for item_in in items_to_order:
            order_item = _validate_and_snapshot_item(db, item_in)
            subtotal += Decimal(str(order_item.line_total))
            order_items.append(order_item)

        shipping_fee = Decimal(str(area.shipping_fee or 0))
        discount_amount = Decimal("0")
        total_amount = max(Decimal("0"), subtotal + shipping_fee - discount_amount)

        # 5. Chống bấm đặt 2 lần (kiểm tra idempotency_key và đơn trùng vừa tạo)
        effective_idem_key = idempotency_key or data.idempotency_key
        fingerprint = _check_duplicate_submission(
            db=db,
            user_id=user_id,
            data=data,
            subtotal=subtotal,
            total_amount=total_amount,
            order_items=order_items,
            idempotency_key=effective_idem_key,
        )

        # 6. Tạo đơn (trạng thái PENDING - Chờ xác nhận) + chi tiết + lịch sử + xoá giỏ trong 1 transaction
        order = Order(
            order_code=generate_order_code(),
            user_id=user_id,
            recipient_name=data.recipient_name.strip(),
            recipient_phone=data.recipient_phone.strip(),
            delivery_address=data.delivery_address.strip(),
            delivery_area_id=area.id,
            shipping_fee=shipping_fee,
            discount_amount=discount_amount,
            subtotal=subtotal,
            total_amount=total_amount,
            payment_method=data.payment_method.value,
            desired_delivery_at=data.desired_delivery_at,
            status="PENDING",
            items=order_items,
        )
        db.add(order)
        db.flush()

        initial_history = OrderStatusHistory(
            order_id=order.id,
            old_status=None,
            new_status="PENDING",
            changed_by=user_id,
            note="Khách hàng tạo đơn hàng (Chờ xác nhận)",
        )
        db.add(initial_history)

        # Xoá toàn bộ các món trong giỏ hàng của user trong cùng transaction
        if cart is not None and cart.items:
            for c_item in list(cart.items):
                db.delete(c_item)

        db.commit()
        db.refresh(order)

        now_done = datetime.now()
        _RECENT_SUBMISSION_CACHE[user_id] = (now_done, fingerprint, order.order_code)
        if effective_idem_key:
            _IDEMPOTENCY_CACHE[(user_id, effective_idem_key.strip())] = (now_done, order.id)

        return order
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể tạo đơn hàng, giao dịch đã được hoàn tác (rollback): {exc}",
        ) from exc
    finally:
        with _GLOBAL_LOCK:
            _USER_ACTIVE_ORDERS.discard(user_id)


def cancel_order(
    db: Session,
    order_id: int,
    user_id: int | None,
    reason: str,
    role: str | None = None,
) -> Order:
    """API huỷ đơn hàng theo điều kiện:
    - Khách huỷ khi còn Chờ xác nhận (PENDING).
    - Nhân viên huỷ trước Đang giao (PENDING, CONFIRMED, PREPARING) kèm lý do (VD: hết món).
    - Ghi lịch sử trạng thái OrderStatusHistory.
    """
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy đơn hàng id={order_id}",
        )

    if order.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Đơn hàng đã được huỷ trước đó",
        )

    if order.status == "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Không thể huỷ đơn hàng đã hoàn thành",
        )

    user = db.get(User, user_id) if user_id is not None else None
    detected_role = role.upper() if role else (user.role.upper() if user and user.role else "CUSTOMER")

    if detected_role == "CUSTOMER":
        if user_id is not None and order.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền huỷ đơn hàng của người khác",
            )
        if order.status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=f"Khách hàng chỉ có thể huỷ đơn khi đơn ở trạng thái Chờ xác nhận (PENDING). Trạng thái hiện tại: {order.status}",
            )
        cancellation_note = reason.strip() if (reason and reason.strip()) else "Khách hàng huỷ đơn"
    elif detected_role in ("STAFF", "ADMIN", "EMPLOYEE"):
        if order.status in ("DELIVERING", "COMPLETED"):
            raise HTTPException(
                status_code=400,
                detail=f"Nhân viên chỉ có thể huỷ đơn trước khi Đang giao (DELIVERING). Trạng thái hiện tại: {order.status}",
            )
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=400,
                detail="Nhân viên huỷ đơn bắt buộc phải có lý do (ví dụ: hết món)",
            )
        cancellation_note = f"Nhân viên huỷ đơn: {reason.strip()}"
    else:
        if not is_valid_status_transition(order.status, "CANCELLED"):
            raise HTTPException(
                status_code=400,
                detail=f"Không thể huỷ đơn hàng từ trạng thái {order.status}",
            )
        cancellation_note = reason.strip() if reason else "Huỷ đơn hàng"

    old_status = order.status
    order.status = "CANCELLED"

    history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status="CANCELLED",
        changed_by=user_id,
        note=cancellation_note,
    )
    db.add(history)
    db.commit()
    db.refresh(order)
    return order


def change_order_status(
    db: Session,
    order: Order,
    new_status: str,
    changed_by: int | None = None,
    note: str | None = None,
) -> Order:
    """Cập nhật trạng thái đơn hàng theo bảng chuyển trạng thái hợp lệ và lưu lịch sử."""
    if not is_valid_status_transition(order.status, new_status):
        allowed = VALID_STATUS_TRANSITIONS.get(order.status, [])
        raise HTTPException(
            status_code=400,
            detail=f"Không thể chuyển trạng thái từ '{order.status}' sang '{new_status}'. Luồng hợp lệ: {allowed}",
        )

    old_status = order.status
    order.status = new_status
    history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        note=note or f"Chuyển trạng thái sang {new_status}",
    )
    db.add(history)
    db.commit()
    db.refresh(order)
    return order
