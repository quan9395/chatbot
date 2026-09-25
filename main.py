from contextlib import asynccontextmanager

from fastapi import FastAPI
from google import genai

from core.config import settings
from db.database import close_pool, init_pool
from routers import chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create shared resources once.
    await init_pool()
    app.state.gemini_client = genai.Client(
        api_key=settings.gemini_api_key
    )
    app.state.gemini_model = settings.gemini_model

    yield

    # Shutdown: close shared resources once.
    await close_pool()


app = FastAPI(
    title="Chatbot API",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(chat.router)


@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "model": settings.gemini_model,
    }