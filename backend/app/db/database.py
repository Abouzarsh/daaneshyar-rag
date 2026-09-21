from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.rag.text import normalize_persian, search_tokens
from app.rag.types import Chunk


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    """Thread-safe SQLite repository with a small FTS5 lexical index."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            str(path),
            check_same_thread=False,
            timeout=30,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = NORMAL")
        self._create_schema()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        with self._lock:
            cursor = self._connection.cursor()
            try:
                yield cursor
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise
            finally:
                cursor.close()

    def _create_schema(self) -> None:
        with self.transaction() as cursor:
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    stored_name TEXT NOT NULL,
                    mime_type TEXT,
                    size_bytes INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    status TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_documents_checksum
                    ON documents(checksum);
                CREATE INDEX IF NOT EXISTS idx_documents_status
                    ON documents(status);

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    normalized_content TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    page_number INTEGER,
                    heading TEXT,
                    word_count INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_document
                    ON chunks(document_id, chunk_index);

                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    document_id UNINDEXED,
                    content,
                    tokenize='unicode61 remove_diacritics 2'
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    citations_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id, created_at);
                """
            )

    def create_document(
        self,
        *,
        document_id: str,
        name: str,
        stored_name: str,
        mime_type: str | None,
        size_bytes: int,
        checksum: str,
        status: str = "queued",
    ) -> dict[str, Any]:
        now = utc_now()
        with self.transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (
                    id, name, stored_name, mime_type, size_bytes, checksum,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    name,
                    stored_name,
                    mime_type,
                    size_bytes,
                    checksum,
                    status,
                    now,
                    now,
                ),
            )
        document = self.get_document(document_id)
        assert document is not None
        return document

    def update_document(
        self,
        document_id: str,
        *,
        status: str,
        chunk_count: int | None = None,
        error: str | None = None,
    ) -> None:
        fields = ["status = ?", "error = ?", "updated_at = ?"]
        values: list[Any] = [status, error, utc_now()]
        if chunk_count is not None:
            fields.append("chunk_count = ?")
            values.append(chunk_count)
        values.append(document_id)
        with self.transaction() as cursor:
            cursor.execute(
                f"UPDATE documents SET {', '.join(fields)} WHERE id = ?",
                values,
            )

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        return dict(row) if row else None

    def find_active_document_by_checksum(self, checksum: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM documents
                WHERE checksum = ? AND status IN ('queued', 'indexing', 'ready')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (checksum,),
            ).fetchone()
        return dict(row) if row else None

    def list_documents(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def save_chunks(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return
        with self.transaction() as cursor:
            cursor.executemany(
                """
                INSERT INTO chunks (
                    id, document_id, content, normalized_content, chunk_index,
                    page_number, heading, word_count, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.id,
                        chunk.document_id,
                        chunk.content,
                        chunk.normalized_content,
                        chunk.chunk_index,
                        chunk.page_number,
                        chunk.heading,
                        chunk.word_count,
                        json.dumps(chunk.metadata, ensure_ascii=False),
                    )
                    for chunk in chunks
                ],
            )
            cursor.executemany(
                """
                INSERT INTO chunks_fts (chunk_id, document_id, content)
                VALUES (?, ?, ?)
                """,
                [
                    (chunk.id, chunk.document_id, chunk.normalized_content)
                    for chunk in chunks
                ],
            )

    def delete_chunks(self, document_id: str) -> None:
        with self.transaction() as cursor:
            cursor.execute(
                "DELETE FROM chunks_fts WHERE document_id = ?",
                (document_id,),
            )
            cursor.execute(
                "DELETE FROM chunks WHERE document_id = ?",
                (document_id,),
            )

    def get_chunks(self, chunk_ids: Sequence[str]) -> list[dict[str, Any]]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" for _ in chunk_ids)
        with self._lock:
            rows = self._connection.execute(
                f"""
                SELECT
                    c.*,
                    d.name AS document_name
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.id IN ({placeholders})
                """,
                tuple(chunk_ids),
            ).fetchall()
        by_id = {row["id"]: dict(row) for row in rows}
        return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]

    def search_lexical(
        self,
        query: str,
        *,
        limit: int,
        document_ids: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        tokens = search_tokens(query)
        if not tokens:
            return []
        fts_query = " OR ".join(f'"{token.replace(chr(34), "")}"' for token in tokens)
        parameters: list[Any] = [fts_query]
        document_clause = ""
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            document_clause = f"AND document_id IN ({placeholders})"
            parameters.extend(document_ids)
        parameters.append(limit)
        with self._lock:
            rows = self._connection.execute(
                f"""
                SELECT chunk_id, document_id, bm25(chunks_fts) AS rank
                FROM chunks_fts
                WHERE chunks_fts MATCH ?
                {document_clause}
                ORDER BY rank
                LIMIT ?
                """,
                tuple(parameters),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_document(self, document_id: str) -> dict[str, Any] | None:
        document = self.get_document(document_id)
        if not document:
            return None
        with self.transaction() as cursor:
            cursor.execute(
                "DELETE FROM chunks_fts WHERE document_id = ?",
                (document_id,),
            )
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return document

    def create_conversation(self, first_question: str) -> dict[str, Any]:
        conversation_id = str(uuid.uuid4())
        clean_title = normalize_persian(first_question).replace("\n", " ").strip()
        title = clean_title[:67] + "..." if len(clean_title) > 70 else clean_title
        title = title or "گفت‌وگوی جدید"
        now = utc_now()
        with self.transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, title, now, now),
            )
        return {
            "id": conversation_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }

    def add_message(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        citations: Sequence[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid.uuid4())
        now = utc_now()
        citations_json = json.dumps(list(citations or []), ensure_ascii=False)
        with self.transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO messages (
                    id, conversation_id, role, content, citations_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    citations_json,
                    now,
                ),
            )
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "citations": list(citations or []),
            "created_at": now,
        }

    def recent_messages(
        self,
        conversation_id: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()
        messages = [self._message_dict(row) for row in rows]
        messages.reverse()
        return messages

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT
                    c.*,
                    COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self._lock:
            conversation = self._connection.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if not conversation:
                return None
            rows = self._connection.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at
                """,
                (conversation_id,),
            ).fetchall()
        result = dict(conversation)
        result["messages"] = [self._message_dict(row) for row in rows]
        return result

    def delete_conversation(self, conversation_id: str) -> bool:
        with self.transaction() as cursor:
            cursor.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            return cursor.rowcount > 0

    def stats(self) -> dict[str, int]:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM documents WHERE status = 'ready')
                        AS document_count,
                    (SELECT COUNT(*) FROM chunks) AS chunk_count,
                    (SELECT COUNT(*) FROM conversations) AS conversation_count,
                    (SELECT COUNT(*) FROM messages WHERE role = 'user')
                        AS question_count
                """
            ).fetchone()
        return dict(row)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @staticmethod
    def _message_dict(row: sqlite3.Row) -> dict[str, Any]:
        message = dict(row)
        message["citations"] = json.loads(message.pop("citations_json") or "[]")
        return message
