from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_container
from app.api.schemas import ChatRequest
from app.container import AppContainer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    container: Annotated[AppContainer, Depends(get_container)],
) -> StreamingResponse:
    if request.conversation_id and not container.database.get_conversation(
        request.conversation_id
    ):
        raise HTTPException(status_code=404, detail="Conversation not found")

    if request.document_ids:
        known = {
            str(document["id"])
            for document in container.database.list_documents()
            if document["status"] == "ready"
        }
        invalid = set(request.document_ids) - known
        if invalid:
            raise HTTPException(
                status_code=400,
                detail="One or more selected documents are unavailable",
            )

    async def events() -> AsyncIterator[str]:
        try:
            async for event, data in container.pipeline.stream_answer(
                question=request.question,
                conversation_id=request.conversation_id,
                document_ids=request.document_ids,
                top_k=request.top_k,
            ):
                yield _sse(event, data)
        except Exception as exc:
            logger.exception("chat_stream_failed")
            if container.settings.debug:
                detail = f"{type(exc).__name__}: {exc}"
            else:
                detail = (
                    "پاسخ‌گویی کامل نشد. اتصال مدل زبانی و تنظیمات سرویس را بررسی کنید."
                )
            yield _sse(
                "error",
                {"message": detail, "code": type(exc).__name__},
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
