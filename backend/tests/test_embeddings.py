from __future__ import annotations

import math

from app.rag.embeddings import OllamaEmbeddingProvider


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"embeddings": [[3.0, 4.0], [0.0, 2.0]]}


class FakeClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def post(self, url: str, json: dict) -> FakeResponse:
        assert url == "http://localhost:11434/api/embed"
        assert json["model"] == "embeddinggemma"
        assert json["input"] == ["متن اول", "متن دوم"]
        return FakeResponse()

    def get(self, url: str) -> FakeResponse:
        assert url == "http://localhost:11434/api/tags"
        response = FakeResponse()
        response.json = lambda: {"models": [{"name": "embeddinggemma:latest"}]}
        return response


def test_ollama_embeddings_are_batched_and_normalized(monkeypatch):
    monkeypatch.setattr("app.rag.embeddings.httpx.Client", FakeClient)
    provider = OllamaEmbeddingProvider(
        "embeddinggemma",
        base_url="http://localhost:11434",
        batch_size=8,
    )

    vectors = provider.embed_documents(["متن اول", "متن دوم"])

    assert vectors[0] == [0.6, 0.8]
    assert math.isclose(vectors[1][1], 1.0)
    assert provider.dimensions == 2


def test_ollama_embedding_health_checks_the_requested_model(monkeypatch):
    monkeypatch.setattr("app.rag.embeddings.httpx.Client", FakeClient)
    provider = OllamaEmbeddingProvider(
        "embeddinggemma",
        base_url="http://localhost:11434",
    )

    health = provider.health()

    assert health == {
        "ok": True,
        "provider": "ollama",
        "model": "embeddinggemma",
        "detail": "ready",
    }
