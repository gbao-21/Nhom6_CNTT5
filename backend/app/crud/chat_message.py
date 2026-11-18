"""CRUD thao tác với bảng chat_messages."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.schemas.chat_message import ChatMessageCreate


def send_message(db: Session, data: ChatMessageCreate) -> ChatMessage:
    """Gửi tin nhắn mới."""
    msg = ChatMessage(
        customer_id=data.customer_id,
        sender_id=data.sender_id,
        content=data.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(db: Session, customer_id: int, since: Optional[int] = None) -> list[ChatMessage]:
    """Lấy toàn bộ tin nhắn của 1 cuộc trò chuyện (theo customer_id).
    Nếu since được cung cấp, chỉ lấy các tin có id > since (để polling lấy tin mới).
    """
    query = db.query(ChatMessage).filter(ChatMessage.customer_id == customer_id)
    if since is not None:
        query = query.filter(ChatMessage.id > since)
    return query.order_by(ChatMessage.id.asc()).all()


def mark_read(db: Session, customer_id: int, reader_sender_id: int) -> int:
    """Đánh dấu đã đọc tất cả tin nhắn của cuộc trò chuyện mà người đọc không phải là người gửi.
    Trả về số tin được đánh dấu.
    """
    updated = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.customer_id == customer_id,
            ChatMessage.sender_id != reader_sender_id,
            ChatMessage.is_read == False,  # noqa: E712
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return updated


def get_unread_count(db: Session, customer_id: int, reader_sender_id: int) -> int:
    """Đếm số tin nhắn chưa đọc mà người dùng reader_sender_id chưa đọc trong cuộc chat."""
    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.customer_id == customer_id,
            ChatMessage.sender_id != reader_sender_id,
            ChatMessage.is_read == False,  # noqa: E712
        )
        .count()
    )


def get_conversation_list(db: Session) -> list[dict]:
    """Danh sách các cuộc trò chuyện (nhóm theo customer_id), kèm số tin chưa đọc bởi staff.
    Trả về list dict: customer_id, unread_count (tin khách gửi chưa đọc), last_message.
    """
    from sqlalchemy import func

    # Lấy id tin nhắn cuối cùng của mỗi customer
    subq = (
        db.query(
            ChatMessage.customer_id,
            func.max(ChatMessage.id).label("last_id"),
        )
        .filter(ChatMessage.customer_id.isnot(None))
        .group_by(ChatMessage.customer_id)
        .subquery()
    )

    rows = (
        db.query(ChatMessage)
        .join(subq, ChatMessage.id == subq.c.last_id)
        .order_by(ChatMessage.id.desc())
        .all()
    )

    result = []
    for last_msg in rows:
        # Đếm tin chưa đọc mà khách gửi (sender_id == customer_id)
        unread = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.customer_id == last_msg.customer_id,
                ChatMessage.sender_id == last_msg.customer_id,
                ChatMessage.is_read == False,  # noqa: E712
            )
            .count()
        )
        result.append(
            {
                "customer_id": last_msg.customer_id,
                "unread_count": unread,
                "last_message_id": last_msg.id,
                "last_content": last_msg.content,
                "last_sent_at": last_msg.sent_at,
            }
        )
    return result

