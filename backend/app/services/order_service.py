"""Service xử lý nghiệp vụ đặt hàng (Order)."""
from datetime import datetime
from decimal import Decimal
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.delivery_area import DeliveryArea
from app.models.dish import Dish, DishOption
from app.models.order import Order, OrderItem
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
    total_amount = subtotal + shipping_fee - discount_amount

    order = Order(
        order_code=generate_order_code(),
        user_id=user_id,
        recipient_name=data.recipient_name,
        recipient_phone=data.recipient_phone,
        delivery_address=data.delivery_address,
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
    db.commit()
    db.refresh(order)
    return order

