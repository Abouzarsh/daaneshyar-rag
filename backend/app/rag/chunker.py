from __future__ import annotations

import re
import uuid
from collections.abc import Iterable

from app.rag.text import normalize_persian
from app.rag.types import Chunk, PageText

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?؟؛:])\s+|\n+")


class TextChunker:
    """Sentence-aware chunker with word overlap.

    Word windows are deliberately used instead of model-specific tokenizers so
    ingestion stays deterministic when the embedding model changes.
    """

    def __init__(self, chunk_size_words: int = 220, overlap_words: int = 40):
        if overlap_words >= chunk_size_words:
            raise ValueError("overlap_words must be smaller than chunk_size_words")
        self.chunk_size_words = chunk_size_words
        self.overlap_words = overlap_words

    def split(self, document_id: str, pages: Iterable[PageText]) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 0
        for page in pages:
            normalized = normalize_persian(page.text)
            if not normalized:
                continue
            for content in self._split_page(normalized):
                chunk_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"daaneshyar:{document_id}:{chunk_index}:{content[:80]}",
                    )
                )
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        document_id=document_id,
                        content=content,
                        normalized_content=normalize_persian(content).lower(),
                        chunk_index=chunk_index,
                        page_number=page.page_number,
                        heading=page.heading,
                        word_count=len(content.split()),
                    )
                )
                chunk_index += 1
        return chunks

    def _split_page(self, text: str) -> list[str]:
        sentences = [
            sentence.strip()
            for sentence in _SENTENCE_BOUNDARY.split(text)
            if sentence.strip()
        ]
        if not sentences:
            return []

        chunks: list[str] = []
        current_words: list[str] = []
        for sentence in sentences:
            words = sentence.split()
            if len(words) > self.chunk_size_words:
                if current_words:
                    chunks.append(" ".join(current_words))
                    current_words = []
                chunks.extend(self._window_long_sentence(words))
                continue

            if (
                current_words
                and len(current_words) + len(words) > self.chunk_size_words
            ):
                chunks.append(" ".join(current_words))
                overlap = (
                    current_words[-self.overlap_words :] if self.overlap_words else []
                )
                current_words = [*overlap, *words]
            else:
                current_words.extend(words)

        if current_words:
            candidate = " ".join(current_words)
            if not chunks or candidate != chunks[-1]:
                chunks.append(candidate)
        return chunks

    def _window_long_sentence(self, words: list[str]) -> list[str]:
        step = max(1, self.chunk_size_words - self.overlap_words)
        return [
            " ".join(words[start : start + self.chunk_size_words])
            for start in range(0, len(words), step)
            if words[start : start + self.chunk_size_words]
        ]
