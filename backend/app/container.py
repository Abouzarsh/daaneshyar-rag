from __future__ import annotations

from app.core.config import Settings
from app.db.database import Database
from app.rag.chunker import TextChunker
from app.rag.embeddings import build_embedding_provider
from app.rag.llm import build_llm_provider
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import HybridRetriever
from app.rag.vector_store import build_vector_store
from app.services.ingestion import DocumentService, IngestionService


class AppContainer:
    """Explicit dependency container to keep framework code thin."""

    def __init__(self, settings: Settings):
        self.settings = settings
        settings.prepare_directories()

        embedding_provider = (
            "hash" if settings.demo_mode else settings.embedding_provider
        )
        vector_backend = "memory" if settings.demo_mode else settings.vector_backend
        llm_provider = "demo" if settings.demo_mode else settings.llm_provider

        self.database = Database(settings.database_path)
        self.embeddings = build_embedding_provider(
            provider=embedding_provider,
            model_name=settings.embedding_model,
            device=settings.embedding_device,
            batch_size=settings.embedding_batch_size,
            hash_dimensions=settings.hash_embedding_dimensions,
            ollama_base_url=settings.ollama_base_url,
            ollama_keep_alive=settings.ollama_keep_alive,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        self.vector_store = build_vector_store(
            backend=vector_backend,
            collection_name=settings.qdrant_collection,
            local_path=settings.qdrant_local_path,
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        self.llm = build_llm_provider(
            provider=llm_provider,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
            ollama_keep_alive=settings.ollama_keep_alive,
            openai_base_url=settings.openai_base_url,
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
            temperature=settings.llm_temperature,
            context_window=settings.llm_context_window,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        self.chunker = TextChunker(
            chunk_size_words=settings.chunk_size_words,
            overlap_words=settings.chunk_overlap_words,
        )
        self.retriever = HybridRetriever(
            database=self.database,
            embeddings=self.embeddings,
            vector_store=self.vector_store,
            dense_candidates=settings.dense_candidate_count,
            lexical_candidates=settings.lexical_candidate_count,
            dense_weight=settings.dense_weight,
            lexical_weight=settings.lexical_weight,
            max_chunks_per_document=settings.max_chunks_per_document,
        )
        self.ingestion = IngestionService(
            database=self.database,
            chunker=self.chunker,
            embeddings=self.embeddings,
            vector_store=self.vector_store,
        )
        self.documents = DocumentService(
            database=self.database,
            vector_store=self.vector_store,
            uploads_path=settings.uploads_path,
        )
        self.pipeline = RAGPipeline(
            database=self.database,
            retriever=self.retriever,
            llm=self.llm,
            default_top_k=settings.retrieval_top_k,
            history_limit=settings.conversation_history_messages,
        )

    def close(self) -> None:
        self.vector_store.close()
        self.database.close()
