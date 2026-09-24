import asyncio

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request

from db.database import get_conn
from schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(
    msg: ChatRequest,
    request: Request,
    conn=Depends(get_conn),
):
    # Check that the conversation exists before saving messages.
    conversation = await conn.fetchrow(
        "SELECT id FROM conversations WHERE id = $1",
        msg.conversation_id,
    )
    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {msg.conversation_id} was not found.",
        )

    try:
        # 1. Save the user's message.
        user_row = await conn.fetchrow(
            """
            INSERT INTO messages (role, content, conversation_id)
            VALUES ($1, $2, $3)
            RETURNING id, role, content, conversation_id, created_at
            """,
            "user",
            msg.content,
            msg.conversation_id,
        )

        # 2. Ask Gemini. asyncio.to_thread prevents this synchronous SDK
        # call from blocking FastAPI's async event loop.
        gemini_response = await asyncio.to_thread(
            request.app.state.gemini_client.models.generate_content,
            model=request.app.state.gemini_model,
            contents=msg.content,
        )

        assistant_text = (gemini_response.text or "").strip()
        if not assistant_text:
            raise RuntimeError("Gemini returned an empty response.")

        # 3. Save Gemini's answer.
        assistant_row = await conn.fetchrow(
            """
            INSERT INTO messages (role, content, conversation_id)
            VALUES ($1, $2, $3)
            RETURNING id, role, content, conversation_id, created_at
            """,
            "assistant",
            assistant_text,
            msg.conversation_id,
        )

        # 4. Return both database rows.
        return ChatResponse(
            user_message=MessageResponse(**dict(user_row)),
            assistant_message=MessageResponse(**dict(assistant_row)),
        )

    except asyncpg.PostgresError as exc:
        print(f"PostgreSQL error: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Database operation failed.",
        ) from exc

    except Exception as exc:
        print(f"Gemini error: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Gemini could not generate a response.",
        ) from exc


@router.get("/history", response_model=list[MessageResponse])
async def get_history(
    conversation_id: int,
    conn=Depends(get_conn),
):
    rows = await conn.fetch(
        """
        SELECT id, role, content, conversation_id, created_at
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at, id
        """,
        conversation_id,
    )
    return [dict(row) for row in rows]


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    payload: ConversationCreate,
    conn=Depends(get_conn),
):
    row = await conn.fetchrow(
        """
        INSERT INTO conversations (title)
        VALUES ($1)
        RETURNING id, title
        """,
        payload.title,
    )
    return dict(row)