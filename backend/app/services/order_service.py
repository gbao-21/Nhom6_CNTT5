"""Service xử lý nghiệp vụ đặt hàng (Order)."""
from datetime import datetime
from decimal import Decimal
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.order_status import VALID_STATUS_TRANSITIONS, is_valid_status_transition
from app.crud import coupon as coupon_crud
from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish, DishOption
from app.models.order import Order, OrderItem, OrderStatusHistory
from app.models.user import User
from app.schemas.order import OrderCreate


def generate_order_code() -> str:
    timestamp = datetime.now().strftime("%y%m%d%H%M")
    suffix = uuid.uuid4().hex[:4].upper()
    return f"ORD-{timestamp}-{suffix}"


def create_order_for_user(db: Session, user_id: int, data: OrderCreate) -> Order:
    area = db.get(DeliveryArea, data.delivery_area_id)
    if area is None or not area.is_active:
        raise HTTPException(status_code=404, detail="Khu vực giao hàng không hợp lệ")

    shipping_fee = Decimal(area.shipping_fee)
    subtotal = Decimal("0")
    order_items: list[OrderItem] = []

    for item_in in data.items:
        dish = db.get(Dish, item_in.dish_id)
        if dish is None or not dish.is_available:
            raise HTTPException(
                status_code=404,
                detail=f"Món ăn id={item_in.dish_id} không tồn tại hoặc đã ngừng bán",
            )

        dish_price = Decimal(dish.price)
        options_price = Decimal("0")
        selected_options_snapshot: list[dict] = []

        for opt_in in item_in.selected_options:
            opt = db.get(DishOption, opt_in.option_id)
            if opt is None or opt.dish_id != dish.id or not opt.is_available:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tùy chọn id={opt_in.option_id} không hợp lệ cho món {dish.name}",
                )
            opt_price = Decimal(opt.price)
            options_price += opt_price
            selected_options_snapshot.append(
                {
                    "option_id": opt.id,
                    "name": opt.name,
                    "price": float(opt_price),
                }
            )

        line_total = (dish_price + options_price) * item_in.quantity
        subtotal += line_total

        order_items.append(
            OrderItem(
                dish_id=dish.id,
                dish_name=dish.name,
                dish_price=dish_price,
                selected_options=selected_options_snapshot,
                options_price=options_price,
                note=item_in.note,
                quantity=item_in.quantity,
                line_total=line_total,
            )
        )

    discount_amount = Decimal("0")
    coupon_applied = None
    if data.coupon_code and data.coupon_code.strip():
        coupon_applied, discount_amount = coupon_crud.validate_and_get_discount(
            db=db,
            code=data.coupon_code,
            order_amount=subtotal,
        )

    total_amount = max(Decimal("0"), subtotal + shipping_fee - discount_amount)

    order = Order(
        order_code=generate_order_code(),
        user_id=user_id,
        recipient_name=data.recipient_name,
        recipient_phone=data.recipient_phone,
        delivery_address=data.delivery_address,
        delivery_area_id=area.id,
        shipping_fee=shipping_fee,
        coupon_code=coupon_applied.code if coupon_applied else None,
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

    if coupon_applied is not None:
        coupon_crud.increment_used_count(db, coupon_applied)

    initial_history = OrderStatusHistory(
        order_id=order.id,
        old_status=None,
        new_status="PENDING",
        changed_by=user_id,
        note="Khách hàng tạo đơn hàng",
    )
    db.add(initial_history)

    db.commit()
    db.refresh(order)
    return order


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
        # Khách hàng chỉ được huỷ đơn của chính mình
        if user_id is not None and order.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền huỷ đơn hàng của người khác",
            )
        # Khách huỷ khi còn Chờ xác nhận
        if order.status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=f"Khách hàng chỉ có thể huỷ đơn khi đơn ở trạng thái Chờ xác nhận (PENDING). Trạng thái hiện tại: {order.status}",
            )
        cancellation_note = reason.strip() if (reason and reason.strip()) else "Khách hàng huỷ đơn"
    elif detected_role in ("STAFF", "ADMIN", "EMPLOYEE"):
        # Nhân viên huỷ trước Đang giao kèm lý do (VD: hết món)
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
        # Kiểm tra theo bảng chuyển trạng thái hợp lệ
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


