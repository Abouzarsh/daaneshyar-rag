from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables.

    Every setting is prefixed with RAG_. The defaults intentionally favor
    a private, local-first setup that works well for a portfolio demo.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_prefix="RAG_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Daaneshyar RAG"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    data_dir: Path = Path("./data")
    database_filename: str = "daaneshyar.sqlite3"
    uploads_dirname: str = "uploads"

    max_upload_mb: int = Field(default=25, ge=1, le=250)
    allowed_extensions: str = ".pdf,.docx,.txt,.md"
    chunk_size_words: int = Field(default=220, ge=80, le=800)
    chunk_overlap_words: int = Field(default=40, ge=0, le=200)
    embedding_batch_size: int = Field(default=32, ge=1, le=256)

    embedding_provider: str = "ollama"
    embedding_model: str = "embeddinggemma"
    embedding_device: str | None = None
    hash_embedding_dimensions: int = Field(default=256, ge=64, le=2048)

    vector_backend: str = "qdrant"
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str = "daaneshyar_chunks_v1"
    qdrant_local_dirname: str = "qdrant"

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_keep_alive: str = "10m"
    llm_temperature: float = Field(default=0.15, ge=0.0, le=2.0)
    llm_context_window: int = Field(default=8192, ge=2048, le=131072)
    llm_timeout_seconds: float = Field(default=180.0, ge=10.0, le=600.0)

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    retrieval_top_k: int = Field(default=6, ge=1, le=20)
    dense_candidate_count: int = Field(default=18, ge=1, le=100)
    lexical_candidate_count: int = Field(default=18, ge=1, le=100)
    dense_weight: float = Field(default=0.65, ge=0.0, le=1.0)
    lexical_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    max_chunks_per_document: int = Field(default=3, ge=1, le=10)
    conversation_history_messages: int = Field(default=8, ge=0, le=30)

    demo_mode: bool = False

    @field_validator("embedding_provider", mode="before")
    @classmethod
    def normalize_embedding_provider(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("vector_backend", "llm_provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return str(value).strip().lower()

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_filename

    @property
    def uploads_path(self) -> Path:
        return self.data_dir / self.uploads_dirname

    @property
    def qdrant_local_path(self) -> Path:
        return self.data_dir / self.qdrant_local_dirname

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def allowed_extension_set(self) -> set[str]:
        return {
            extension.strip().lower()
            for extension in self.allowed_extensions.split(",")
            if extension.strip()
        }

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    def prepare_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_path.mkdir(parents=True, exist_ok=True)
        if self.vector_backend == "qdrant" and not self.qdrant_url:
            self.qdrant_local_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
