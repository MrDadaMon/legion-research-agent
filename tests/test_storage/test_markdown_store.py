import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from src.storage.markdown_store import MarkdownStore
from src.models import ContentItem, compute_content_hash


@pytest.fixture
def temp_knowledge_dir():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def markdown_store(temp_knowledge_dir):
    return MarkdownStore(temp_knowledge_dir)


@pytest.fixture
def sample_content_item_with_id():
    return ContentItem(
        id=1,
        source_type="article",
        source_url="https://example.com/article",
        title="Test Article",
        raw_content="This is the raw content of the test article.",
        processed_date="2026-03-26T12:00:00",
        content_hash="abc123hash",
        reference_count=1,
    )


@pytest.mark.asyncio
async def test_save_and_load_content(markdown_store, sample_content_item_with_id):
    await markdown_store.save(sample_content_item_with_id, "tech")

    loaded = await markdown_store.load("tech", 1)
    assert loaded is not None
    assert loaded.title == "Test Article"
    assert loaded.source_type == "article"
    assert loaded.source_url == "https://example.com/article"
    assert loaded.raw_content == "This is the raw content of the test article."
    assert loaded.content_hash == "abc123hash"
    assert loaded.reference_count == 1


@pytest.mark.asyncio
async def test_delete_content(markdown_store, sample_content_item_with_id):
    await markdown_store.save(sample_content_item_with_id, "science")

    deleted = await markdown_store.delete("science", 1)
    assert deleted is True

    loaded = await markdown_store.load("science", 1)
    assert loaded is None


@pytest.mark.asyncio
async def test_delete_nonexistent(markdown_store):
    deleted = await markdown_store.delete("nonexistent", 999)
    assert deleted is False


@pytest.mark.asyncio
async def test_list_topic_content(markdown_store, sample_content_item_with_id):
    item2 = ContentItem(
        id=2,
        source_type="youtube",
        source_url="https://youtube.com/watch?v=xyz",
        title="Test Video",
        raw_content="Video transcript content.",
        processed_date="2026-03-26T13:00:00",
        content_hash="def456hash",
        reference_count=1,
    )

    await markdown_store.save(sample_content_item_with_id, "media")
    await markdown_store.save(item2, "media")

    content_list = await markdown_store.list_topic_content("media")
    assert len(content_list) == 2
    ids = [cid for cid, title in content_list]
    assert 1 in ids
    assert 2 in ids


@pytest.mark.asyncio
async def test_list_topics(markdown_store, sample_content_item_with_id):
    item2 = ContentItem(
        id=2,
        source_type="pdf",
        source_url=None,
        title="Test PDF",
        raw_content="PDF content here.",
        processed_date="2026-03-26T14:00:00",
        content_hash="ghi789hash",
        reference_count=1,
    )

    await markdown_store.save(sample_content_item_with_id, "ai")
    await markdown_store.save(item2, "papers")

    topics = await markdown_store.list_topics()
    assert "ai" in topics
    assert "papers" in topics


@pytest.mark.asyncio
async def test_load_nonexistent(markdown_store):
    loaded = await markdown_store.load("nonexistent", 999)
    assert loaded is None
