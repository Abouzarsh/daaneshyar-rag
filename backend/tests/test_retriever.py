from pathlib import Path

from app.db.database import Database
from app.rag.chunker import TextChunker
from app.rag.embeddings import HashEmbeddingProvider
from app.rag.retriever import HybridRetriever
from app.rag.types import PageText
from app.rag.vector_store import InMemoryVectorStore


def test_hybrid_retrieval_returns_grounded_chunk(tmp_path: Path):
    database = Database(tmp_path / "test.sqlite3")
    embeddings = HashEmbeddingProvider(128)
    vector_store = InMemoryVectorStore()
    document_id = "doc-network"
    database.create_document(
        document_id=document_id,
        name="راهنمای شبکه.txt",
        stored_name="doc-network.txt",
        mime_type="text/plain",
        size_bytes=120,
        checksum="abc",
        status="ready",
    )
    chunks = TextChunker(80, 10).split(
        document_id,
        [
            PageText(
                text=(
                    "در رخداد قطعی لینک، کارشناس باید ابتدا آلارم‌های انتقال "
                    "را بررسی کند و سپس مسیر پشتیبان را فعال نماید."
                ),
                page_number=2,
            )
        ],
    )
    database.save_chunks(chunks)
    vector_store.upsert(
        chunks,
        embeddings.embed_documents([chunk.content for chunk in chunks]),
    )
    retriever = HybridRetriever(
        database=database,
        embeddings=embeddings,
        vector_store=vector_store,
    )

    results = retriever.retrieve("در زمان قطعی لینک چه کنیم؟", top_k=3)

    assert len(results) == 1
    assert results[0].document_name == "راهنمای شبکه.txt"
    assert results[0].page_number == 2
    assert "keyword" in results[0].retrieval_methods
    database.close()
