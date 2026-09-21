from __future__ import annotations

import math
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from app.rag.types import Chunk, DenseHit


class VectorStore(Protocol):
    def upsert(
        self,
        chunks: Sequence[Chunk],
        vectors: Sequence[Sequence[float]],
    ) -> None: ...

    def search(
        self,
        vector: Sequence[float],
        *,
        limit: int,
        document_ids: Sequence[str] | None = None,
    ) -> list[DenseHit]: ...

    def delete_document(self, document_id: str) -> None: ...

    def health(self) -> dict[str, str | bool]: ...

    def close(self) -> None: ...


class InMemoryVectorStore:
    """Simple cosine store used by tests and offline demo mode."""

    def __init__(self):
        self._items: dict[str, tuple[list[float], str]] = {}
        self._lock = threading.RLock()

    def upsert(
        self,
        chunks: Sequence[Chunk],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have equal lengths")
        with self._lock:
            for chunk, vector in zip(chunks, vectors, strict=True):
                self._items[chunk.id] = (list(vector), chunk.document_id)

    def search(
        self,
        vector: Sequence[float],
        *,
        limit: int,
        document_ids: Sequence[str] | None = None,
    ) -> list[DenseHit]:
        allowed = set(document_ids or [])
        with self._lock:
            scores = [
                DenseHit(
                    chunk_id=chunk_id,
                    score=self._cosine(vector, stored_vector),
                )
                for chunk_id, (stored_vector, document_id) in self._items.items()
                if not allowed or document_id in allowed
            ]
        scores.sort(key=lambda hit: hit.score, reverse=True)
        return scores[:limit]

    def delete_document(self, document_id: str) -> None:
        with self._lock:
            stale = [
                chunk_id
                for chunk_id, (_, stored_document_id) in self._items.items()
                if stored_document_id == document_id
            ]
            for chunk_id in stale:
                self._items.pop(chunk_id, None)

    def health(self) -> dict[str, str | bool]:
        return {"ok": True, "backend": "memory"}

    def close(self) -> None:
        return None

    @staticmethod
    def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)


class QdrantVectorStore:
    """Qdrant adapter supporting either a server URL or embedded local mode."""

    def __init__(
        self,
        *,
        collection_name: str,
        local_path: Path | None = None,
        url: str | None = None,
        api_key: str | None = None,
    ):
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client is not installed. Install backend dependencies "
                "or set RAG_VECTOR_BACKEND=memory."
            ) from exc

        self.collection_name = collection_name
        self._models = self._load_models()
        self._server_mode = bool(url)
        if url:
            self._client = QdrantClient(url=url, api_key=api_key, timeout=30)
        elif local_path:
            self._client = QdrantClient(path=str(local_path))
        else:
            raise ValueError("Either url or local_path is required for Qdrant")
        self._dimensions: int | None = None
        self._lock = threading.RLock()

    @staticmethod
    def _load_models():
        from qdrant_client import models

        return models

    def _ensure_collection(self, dimensions: int) -> None:
        with self._lock:
            if self._dimensions == dimensions:
                return
            if not self._client.collection_exists(self.collection_name):
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=self._models.VectorParams(
                        size=dimensions,
                        distance=self._models.Distance.COSINE,
                    ),
                )
                if self._server_mode:
                    self._client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name="document_id",
                        field_schema=self._models.PayloadSchemaType.KEYWORD,
                    )
            else:
                collection = self._client.get_collection(self.collection_name)
                vector_config = collection.config.params.vectors
                existing_size = getattr(vector_config, "size", None)
                if existing_size and int(existing_size) != dimensions:
                    raise RuntimeError(
                        "Qdrant collection dimensions do not match the current "
                        "embedding model. Use a new collection name or re-index."
                    )
            self._dimensions = dimensions

    def upsert(
        self,
        chunks: Sequence[Chunk],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        if not vectors:
            return
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have equal lengths")
        self._ensure_collection(len(vectors[0]))
        points = [
            self._models.PointStruct(
                id=chunk.id,
                vector=list(vector),
                payload={
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self._client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

    def search(
        self,
        vector: Sequence[float],
        *,
        limit: int,
        document_ids: Sequence[str] | None = None,
    ) -> list[DenseHit]:
        self._ensure_collection(len(vector))
        query_filter = None
        if document_ids:
            query_filter = self._models.Filter(
                must=[
                    self._models.FieldCondition(
                        key="document_id",
                        match=self._models.MatchAny(any=list(document_ids)),
                    )
                ]
            )
        response = self._client.query_points(
            collection_name=self.collection_name,
            query=list(vector),
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return [
            DenseHit(
                chunk_id=str((point.payload or {}).get("chunk_id", point.id)),
                score=float(point.score),
            )
            for point in response.points
        ]

    def delete_document(self, document_id: str) -> None:
        if not self._client.collection_exists(self.collection_name):
            return
        self._client.delete(
            collection_name=self.collection_name,
            points_selector=self._models.Filter(
                must=[
                    self._models.FieldCondition(
                        key="document_id",
                        match=self._models.MatchValue(value=document_id),
                    )
                ]
            ),
            wait=True,
        )

    def health(self) -> dict[str, str | bool]:
        try:
            self._client.get_collections()
            return {"ok": True, "backend": "qdrant"}
        except Exception as exc:
            return {
                "ok": False,
                "backend": "qdrant",
                "detail": type(exc).__name__,
            }

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close:
            close()


def build_vector_store(
    *,
    backend: str,
    collection_name: str,
    local_path: Path,
    url: str | None,
    api_key: str | None,
) -> VectorStore:
    if backend == "memory":
        return InMemoryVectorStore()
    if backend == "qdrant":
        return QdrantVectorStore(
            collection_name=collection_name,
            local_path=None if url else local_path,
            url=url,
            api_key=api_key,
        )
    raise ValueError(f"Unknown vector backend: {backend}")
