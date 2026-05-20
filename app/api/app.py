from __future__ import annotations

from fastapi import FastAPI

from app.api.errors import install_exception_handlers
from app.api.v1.chat import router as chat_router
from app.api.v1.voice import router as voice_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="History Docent RAG API",
        version="0.1.0",
        description="서울/한양 역사 도슨트 RAG 백엔드 API",
    )
    install_exception_handlers(app)
    app.include_router(chat_router)
    app.include_router(voice_router)
    return app
