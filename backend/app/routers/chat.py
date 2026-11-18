"""API chat giữa khách và cửa hàng: /api/chat

Các endpoint:
- POST   /api/chat/messages                 - Gửi tin nhắn (khách hoặc staff)
- GET    /api/chat/messages/{customer_id}   - Lấy lịch sử chat (hỗ trợ ?since=<id>)
- PATCH  /api/chat/messages/{customer_id}/read - Đánh dấu đã đọc
- GET    /api/chat/conversations            - Danh sách cuộc chat (dành cho staff)
"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import chat_message as chat_crud
from app.db.session import get_db
from app.schemas.chat_message import (
    ChatMessageCreate,
    ChatMessageResponse,
    ConversationSummary,
    MarkReadResponse,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/messages", response_model=ChatMessageResponse, status_code=201, summary="Gửi tin nhắn")
def send_message(data: ChatMessageCreate, db: Session = Depends(get_db)):
    return chat_crud.send_message(db, data)


@router.get(
    "/messages/{customer_id}",
    response_model=list[ChatMessageResponse],
    summary="Lấy lịch sử chat. Truyền ?since=<id> để chỉ lấy tin mới hơn id đó.",
)
def get_messages(
    customer_id: int,
    since: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return chat_crud.get_messages(db, customer_id, since)


@router.patch(
    "/messages/{customer_id}/read",
    response_model=MarkReadResponse,
    summary="Đánh dấu đã đọc. Truyền ?reader_id=<sender_id_của_người_đọc>.",
)
def mark_read(
    customer_id: int,
    reader_id: int,
    db: Session = Depends(get_db),
):
    marked = chat_crud.mark_read(db, customer_id, reader_id)
    return {"marked": marked}


@router.get(
    "/conversations",
    response_model=list[ConversationSummary],
    summary="Danh sách tất cả cuộc trò chuyện (dành cho staff), kèm số tin chưa đọc.",
)
def list_conversations(db: Session = Depends(get_db)):
    return chat_crud.get_conversation_list(db)

