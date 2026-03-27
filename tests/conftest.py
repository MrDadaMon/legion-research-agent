import asyncio
import pytest
import os
import tempfile
from pathlib import Path


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)
    wal_path = db_path + "-wal"
    if os.path.exists(wal_path):
        os.unlink(wal_path)
    shm_path = db_path + "-shm"
    if os.path.exists(shm_path):
        os.unlink(shm_path)


@pytest.fixture
def sample_content_item():
    from src.models import ContentItem, compute_content_hash

    return ContentItem(
        id=None,
        source_type="article",
        source_url="https://example.com/article",
        title="Test Article",
        raw_content="This is test content for the article.",
        processed_date="2026-03-26T12:00:00",
        content_hash=compute_content_hash("This is test content for the article."),
        reference_count=1,
    )
