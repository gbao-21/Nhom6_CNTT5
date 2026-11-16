"""Pydantic schemas cho ChatMessage."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    customer_id: Optional[int] = None
    sender_id: Optional[int] = None
    content: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    id: int
    customer_id: Optional[int] = None
    sender_id: Optional[int] = None
    content: str
    is_read: bool
    sent_at: datetime

    class Config:
        from_attributes = True

