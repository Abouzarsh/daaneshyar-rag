from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PageText:
    text: str
    page_number: int | None = None
    heading: str | None = None


@dataclass(slots=True)
class Chunk:
    id: str
    document_id: str
    content: str
    normalized_content: str
    chunk_index: int
    page_number: int | None = None
    heading: str | None = None
    word_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DenseHit:
    chunk_id: str
    score: float


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    page_number: int | None
    chunk_index: int
    score: float
    retrieval_methods: list[str]

    def citation_dict(self, index: int) -> dict[str, Any]:
        excerpt = self.content.strip().replace("\n", " ")
        if len(excerpt) > 360:
            excerpt = excerpt[:357].rstrip() + "..."
        return {
            "index": index,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "excerpt": excerpt,
            "score": round(self.score, 4),
            "retrieval_methods": self.retrieval_methods,
        }
