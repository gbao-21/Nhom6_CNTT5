"""Model bảng chat_messages (tin nhắn hỗ trợ giữa khách hàng và cửa hàng).

Yêu cầu:
- khách (customer_id: đại diện cuộc trò chuyện của khách nào)
- người gửi (sender_id: ID người gửi tin, khách hoặc nhân viên)
- nội dung (content: text nội dung tin nhắn)
- đã đọc (is_read: trạng thái xem tin nhắn)
- thời điểm (created_at: thời gian gửi)
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Khách hàng sở hữu cuộc trò chuyện (để gom luồng chat theo khách)
    customer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Người thực tế gửi tin nhắn (khách hàng hoặc nhân viên/admin)
    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Phân loại người gửi: 'CUSTOMER' hoặc 'STAFF' / 'ADMIN'
    sender_role = Column(
        String(30),
        nullable=False,
        default="CUSTOMER",
        server_default="CUSTOMER",
    )

    # Nội dung tin nhắn
    content = Column(Text, nullable=False)

    # Đã đọc hay chưa (True/False)
    is_read = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    # Thời điểm gửi tin nhắn
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    # Quan hệ
    customer = relationship("User", foreign_keys=[customer_id], backref="customer_chats")
    sender = relationship("User", foreign_keys=[sender_id], backref="sent_chats")

