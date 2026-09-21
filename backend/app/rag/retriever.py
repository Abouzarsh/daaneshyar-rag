from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from app.db.database import Database
from app.rag.embeddings import EmbeddingProvider
from app.rag.types import RetrievedChunk
from app.rag.vector_store import VectorStore


class HybridRetriever:
    """Dense + SQLite FTS retrieval fused with weighted reciprocal rank."""

    def __init__(
        self,
        *,
        database: Database,
        embeddings: EmbeddingProvider,
        vector_store: VectorStore,
        dense_candidates: int = 18,
        lexical_candidates: int = 18,
        dense_weight: float = 0.65,
        lexical_weight: float = 0.35,
        max_chunks_per_document: int = 3,
    ):
        self.database = database
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.dense_candidates = dense_candidates
        self.lexical_candidates = lexical_candidates
        self.dense_weight = dense_weight
        self.lexical_weight = lexical_weight
        self.max_chunks_per_document = max_chunks_per_document

    def retrieve(
        self,
        query: str,
        *,
        top_k: int,
        document_ids: Sequence[str] | None = None,
    ) -> list[RetrievedChunk]:
        query_vector = self.embeddings.embed_query(query)
        dense_hits = self.vector_store.search(
            query_vector,
            limit=self.dense_candidates,
            document_ids=document_ids,
        )
        lexical_hits = self.database.search_lexical(
            query,
            limit=self.lexical_candidates,
            document_ids=document_ids,
        )

        rrf_k = 60
        scores: dict[str, float] = defaultdict(float)
        methods: dict[str, set[str]] = defaultdict(set)

        for rank, hit in enumerate(dense_hits, start=1):
            scores[hit.chunk_id] += self.dense_weight / (rrf_k + rank)
            methods[hit.chunk_id].add("semantic")

        for rank, hit in enumerate(lexical_hits, start=1):
            chunk_id = str(hit["chunk_id"])
            scores[chunk_id] += self.lexical_weight / (rrf_k + rank)
            methods[chunk_id].add("keyword")

        ranked_ids = sorted(scores, key=scores.get, reverse=True)
        rows = self.database.get_chunks(ranked_ids)
        max_score = max(scores.values(), default=1.0)
        per_document: dict[str, int] = defaultdict(int)
        results: list[RetrievedChunk] = []

        for row in rows:
            document_id = str(row["document_id"])
            if per_document[document_id] >= self.max_chunks_per_document:
                continue
            chunk_id = str(row["id"])
            results.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_name=str(row["document_name"]),
                    content=str(row["content"]),
                    page_number=row["page_number"],
                    chunk_index=int(row["chunk_index"]),
                    score=scores[chunk_id] / max_score if max_score else 0.0,
                    retrieval_methods=sorted(methods[chunk_id]),
                )
            )
            per_document[document_id] += 1
            if len(results) >= top_k:
                break
        return results
