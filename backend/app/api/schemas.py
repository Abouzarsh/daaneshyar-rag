from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class DocumentOut(BaseModel):
    id: str
    name: str
    mime_type: str | None
    size_bytes: int
    status: Literal["queued", "indexing", "ready", "failed"]
    chunk_count: int
    error: str | None
    created_at: str
    updated_at: str


class UploadItem(BaseModel):
    document: DocumentOut | None = None
    filename: str
    status: Literal["queued", "duplicate", "rejected"]
    detail: str | None = None
    duplicate_of: str | None = None


class UploadResponse(BaseModel):
    items: list[UploadItem]


class DeleteResponse(BaseModel):
    deleted: bool
    id: str


class Citation(BaseModel):
    index: int
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int | None
    excerpt: str
    score: float
    retrieval_methods: list[str]


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation] = Field(default_factory=list)
    created_at: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[MessageOut]


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    conversation_id: str | None = None
    document_ids: list[str] | None = None
    top_k: int | None = Field(default=None, ge=1, le=12)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Question is too short")
        return value


class StatsOut(BaseModel):
    document_count: int
    chunk_count: int
    conversation_count: int
    question_count: int


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    components: dict[str, dict[str, Any]]
