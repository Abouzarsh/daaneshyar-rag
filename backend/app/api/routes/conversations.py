from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_container
from app.api.schemas import (
    ConversationOut,
    ConversationSummary,
    DeleteResponse,
)
from app.container import AppContainer

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[ConversationSummary]:
    return [
        ConversationSummary.model_validate(item)
        for item in container.database.list_conversations()
    ]


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> ConversationOut:
    conversation = container.database.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationOut.model_validate(conversation)


@router.delete("/{conversation_id}", response_model=DeleteResponse)
def delete_conversation(
    conversation_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> DeleteResponse:
    if not container.database.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return DeleteResponse(deleted=True, id=conversation_id)
