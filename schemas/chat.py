from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=20_000)
    conversation_id: int


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    conversation_id: int | None = None
    created_at: datetime


class ChatResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse


class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class ConversationResponse(BaseModel):
    id: int
    title: str | None = None