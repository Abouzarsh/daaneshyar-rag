from __future__ import annotations

import hashlib
import importlib.util
import math
import re
import threading
from collections.abc import Sequence
from typing import Protocol

import httpx

from app.rag.text import normalize_persian

_WORD = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)


class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    @property
    def name(self) -> str: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...

    def health(self) -> dict[str, str | bool]: ...


class HashEmbeddingProvider:
    """Deterministic offline embeddings for tests and the zero-download demo.

    This is not a replacement for a semantic model. It exists so contributors
    can exercise the complete ingestion and chat flow without downloading
    model weights.
    """

    def __init__(self, dimensions: int = 256):
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def name(self) -> str:
        return f"hash-{self.dimensions}"

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def health(self) -> dict[str, str | bool]:
        return {
            "ok": True,
            "provider": "hash",
            "model": self.name,
            "detail": "ready",
        }

    def _embed(self, text: str) -> list[float]:
        normalized = normalize_persian(text).lower()
        vector = [0.0] * self.dimensions
        tokens = _WORD.findall(normalized)

        for token in tokens:
            self._add_feature(vector, token, 1.0)
            padded = f"^{token}$"
            for index in range(max(0, len(padded) - 2)):
                self._add_feature(vector, padded[index : index + 3], 0.25)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def _add_feature(self, vector: list[float], feature: str, weight: float) -> None:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, byteorder="big", signed=False)
        index = value % self.dimensions
        sign = -1.0 if value & 1 else 1.0
        vector[index] += sign * weight


class OllamaEmbeddingProvider:
    """Synchronous Ollama adapter used inside ingestion worker threads."""

    def __init__(
        self,
        model_name: str,
        *,
        base_url: str,
        batch_size: int = 32,
        timeout_seconds: float = 180.0,
        keep_alive: str = "10m",
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self.keep_alive = keep_alive
        self._dimensions = 0

    @property
    def name(self) -> str:
        return f"ollama:{self.model_name}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text])[0]

    def health(self) -> dict[str, str | bool]:
        try:
            with httpx.Client(timeout=3, trust_env=False) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = {
                    item.get("name", "").split(":")[0]
                    for item in response.json().get("models", [])
                }
            wanted = self.model_name.split(":")[0]
            ready = wanted in models
            return {
                "ok": ready,
                "provider": "ollama",
                "model": self.model_name,
                "detail": "ready" if ready else "model_not_pulled",
            }
        except Exception as exc:
            return {
                "ok": False,
                "provider": "ollama",
                "model": self.model_name,
                "detail": type(exc).__name__,
            }

    def _embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": self.model_name,
            "input": list(texts),
            "truncate": True,
            "keep_alive": self.keep_alive,
        }
        with httpx.Client(
            timeout=self.timeout_seconds,
            trust_env=False,
        ) as client:
            response = client.post(f"{self.base_url}/api/embed", json=payload)
            response.raise_for_status()
        vectors = [
            self._normalize(list(vector))
            for vector in response.json().get("embeddings", [])
        ]
        if len(vectors) != len(texts):
            raise RuntimeError("Ollama returned an unexpected embedding count")
        if vectors:
            self._dimensions = len(vectors[0])
        return vectors

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


class SentenceTransformerEmbeddingProvider:
    """Lazy multilingual Sentence Transformers adapter."""

    def __init__(
        self,
        model_name: str,
        *,
        device: str | None = None,
        batch_size: int = 32,
    ):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self.model_name

    @property
    def dimensions(self) -> int:
        model = self._get_model()
        dimensions = model.get_sentence_embedding_dimension()
        if dimensions is None:
            raise RuntimeError("Embedding model did not report its dimensions")
        return int(dimensions)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        prepared = [self._prefix(text, is_query=False) for text in texts]
        return self._encode(prepared)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([self._prefix(text, is_query=True)])[0]

    def health(self) -> dict[str, str | bool]:
        installed = importlib.util.find_spec("sentence_transformers") is not None
        return {
            "ok": installed,
            "provider": "sentence-transformers",
            "model": self.model_name,
            "detail": "configured" if installed else "dependency_missing",
        }

    def _prefix(self, text: str, *, is_query: bool) -> str:
        if "e5" not in self.model_name.lower():
            return text
        return f"{'query' if is_query else 'passage'}: {text}"

    def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._get_model().encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return [vector.tolist() for vector in vectors]

    def _get_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError as exc:
                    raise RuntimeError(
                        "sentence-transformers is not installed. "
                        "Install backend[local-embeddings] or use "
                        "RAG_EMBEDDING_PROVIDER=hash."
                    ) from exc
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                )
        return self._model


def build_embedding_provider(
    *,
    provider: str,
    model_name: str,
    device: str | None,
    batch_size: int,
    hash_dimensions: int,
    ollama_base_url: str,
    ollama_keep_alive: str,
    timeout_seconds: float,
) -> EmbeddingProvider:
    if provider == "hash":
        return HashEmbeddingProvider(hash_dimensions)
    if provider == "ollama":
        return OllamaEmbeddingProvider(
            model_name,
            base_url=ollama_base_url,
            batch_size=batch_size,
            timeout_seconds=timeout_seconds,
            keep_alive=ollama_keep_alive,
        )
    if provider in {"sentence-transformers", "sentence_transformers", "st"}:
        return SentenceTransformerEmbeddingProvider(
            model_name,
            device=device,
            batch_size=batch_size,
        )
    raise ValueError(f"Unknown embedding provider: {provider}")
