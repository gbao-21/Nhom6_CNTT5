"""Model bảng chat_messages (tin nhắn hỗ trợ giữa khách và cửa hàng)."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text, func

from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Khách hàng liên quan đến cuộc trò chuyện
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Người gửi tin nhắn (customer_id hoặc staff user_id)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Nội dung tin nhắn
    content = Column(Text, nullable=False)

    # Đã đọc chưa
    is_read = Column(Boolean, nullable=False, default=False, server_default="0")

    # Thời điểm gửi
    sent_at = Column(DateTime, nullable=False, server_default=func.now())

