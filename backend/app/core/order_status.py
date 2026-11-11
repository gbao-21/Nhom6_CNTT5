"""Định nghĩa luồng trạng thái đơn hàng và bảng chuyển trạng thái hợp lệ.

Luồng trạng thái đơn hàng:
Chờ xác nhận (PENDING) -> Đã xác nhận (CONFIRMED) -> Đang chuẩn bị (PREPARING) -> Đang giao (DELIVERING) -> Hoàn thành (COMPLETED), và Đã huỷ (CANCELLED).
"""
from enum import Enum


class OrderStatusEnum(str, Enum):
    PENDING = "PENDING"          # Chờ xác nhận
    CONFIRMED = "CONFIRMED"      # Đã xác nhận
    PREPARING = "PREPARING"      # Đang chuẩn bị
    DELIVERING = "DELIVERING"    # Đang giao
    COMPLETED = "COMPLETED"      # Hoàn thành
    CANCELLED = "CANCELLED"      # Đã huỷ


ORDER_STATUS_LABELS: dict[str, str] = {
    OrderStatusEnum.PENDING.value: "Chờ xác nhận",
    OrderStatusEnum.CONFIRMED.value: "Đã xác nhận",
    OrderStatusEnum.PREPARING.value: "Đang chuẩn bị",
    OrderStatusEnum.DELIVERING.value: "Đang giao",
    OrderStatusEnum.COMPLETED.value: "Hoàn thành",
    OrderStatusEnum.CANCELLED.value: "Đã huỷ",
}

# Bảng chuyển trạng thái hợp lệ (Valid status transitions)
# - PENDING: có thể chuyển sang CONFIRMED (nhân viên xác nhận) hoặc CANCELLED (khách/nhân viên huỷ)
# - CONFIRMED: có thể chuyển sang PREPARING (bắt đầu làm món) hoặc CANCELLED (nhân viên huỷ kèm lý do)
# - PREPARING: có thể chuyển sang DELIVERING (giao hàng) hoặc CANCELLED (nhân viên huỷ kèm lý do, VD: hết món)
# - DELIVERING: có thể chuyển sang COMPLETED (giao thành công)
# - COMPLETED: trạng thái kết thúc, không thể đổi trạng thái
# - CANCELLED: trạng thái kết thúc, không thể đổi trạng thái
VALID_STATUS_TRANSITIONS: dict[str, list[str]] = {
    OrderStatusEnum.PENDING.value: [
        OrderStatusEnum.CONFIRMED.value,
        OrderStatusEnum.CANCELLED.value,
    ],
    OrderStatusEnum.CONFIRMED.value: [
        OrderStatusEnum.PREPARING.value,
        OrderStatusEnum.CANCELLED.value,
    ],
    OrderStatusEnum.PREPARING.value: [
        OrderStatusEnum.DELIVERING.value,
        OrderStatusEnum.CANCELLED.value,
    ],
    OrderStatusEnum.DELIVERING.value: [
        OrderStatusEnum.COMPLETED.value,
    ],
    OrderStatusEnum.COMPLETED.value: [],
    OrderStatusEnum.CANCELLED.value: [],
}


def is_valid_status_transition(current_status: str, new_status: str) -> bool:
    """Kiểm tra việc chuyển từ current_status sang new_status có hợp lệ không."""
    allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])
    return new_status in allowed_transitions
