from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        demo_mode=True,
        embedding_provider="hash",
        vector_backend="memory",
        llm_provider="demo",
        chunk_size_words=80,
        chunk_overlap_words=12,
    )


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
