from __future__ import annotations

import logging
from pathlib import Path

from app.db.database import Database
from app.rag.chunker import TextChunker
from app.rag.embeddings import EmbeddingProvider
from app.rag.loaders import load_document
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        *,
        database: Database,
        chunker: TextChunker,
        embeddings: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        self.database = database
        self.chunker = chunker
        self.embeddings = embeddings
        self.vector_store = vector_store

    def ingest(self, document_id: str, path: Path) -> None:
        """Extract, chunk, embed, and index one persisted upload."""

        self.database.update_document(document_id, status="indexing")
        try:
            pages = load_document(path)
            chunks = self.chunker.split(document_id, pages)
            if not chunks:
                raise ValueError("Document produced no usable text chunks")

            vectors = self.embeddings.embed_documents(
                [chunk.content for chunk in chunks]
            )
            self.vector_store.upsert(chunks, vectors)
            try:
                self.database.save_chunks(chunks)
            except Exception:
                self.vector_store.delete_document(document_id)
                raise

            self.database.update_document(
                document_id,
                status="ready",
                chunk_count=len(chunks),
            )
            logger.info(
                "document_indexed",
                extra={
                    "document_id": document_id,
                    "chunk_count": len(chunks),
                },
            )
        except Exception as exc:
            logger.exception(
                "document_ingestion_failed",
                extra={"document_id": document_id},
            )
            try:
                self.vector_store.delete_document(document_id)
                self.database.delete_chunks(document_id)
            finally:
                self.database.update_document(
                    document_id,
                    status="failed",
                    chunk_count=0,
                    error=str(exc)[:500],
                )


class DocumentService:
    def __init__(
        self,
        *,
        database: Database,
        vector_store: VectorStore,
        uploads_path: Path,
    ):
        self.database = database
        self.vector_store = vector_store
        self.uploads_path = uploads_path

    def delete(self, document_id: str) -> bool:
        document = self.database.get_document(document_id)
        if not document:
            return False
        self.vector_store.delete_document(document_id)
        deleted = self.database.delete_document(document_id)
        if deleted:
            stored_path = self.uploads_path / str(deleted["stored_name"])
            stored_path.unlink(missing_ok=True)
        return deleted is not None
