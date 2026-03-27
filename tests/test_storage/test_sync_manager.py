import pytest
import asyncio
import tempfile
import os
import shutil
from pathlib import Path
from src.storage.sync_manager import SyncManager
from src.storage.database import Database
from src.storage.markdown_store import MarkdownStore
from src.models import ContentItem, compute_content_hash


@pytest.fixture
def temp_knowledge_dir():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path


@pytest.fixture
def sync_manager(temp_db_path, temp_knowledge_dir):
    db = Database(temp_db_path)
    markdown_store = MarkdownStore(temp_knowledge_dir)
    sm = SyncManager(db, markdown_store)
    yield sm
    try:
        import asyncio
        asyncio.get_event_loop().run_until_complete(db.close())
    except Exception:
        pass


@pytest.fixture
def sample_content_item():
    return ContentItem(
        id=None,
        source_type="article",
        source_url="https://example.com/test",
        title="Sync Test Article",
        raw_content="Content for sync testing.",
        processed_date="2026-03-26T12:00:00",
        content_hash=compute_content_hash("Content for sync testing."),
        reference_count=1,
    )


@pytest.mark.asyncio
async def test_write_content_creates_both(sync_manager, sample_content_item):
    content_id = await sync_manager.write_content(sample_content_item, "testing")
    assert content_id is not None
    assert content_id > 0

    content = await sync_manager.db.get_content(content_id)
    assert content is not None
    assert content.title == "Sync Test Article"

    topics = await sync_manager.db.get_content_topics(content_id)
    assert "testing" in topics

    markdown_path = Path(sync_manager.markdown_store.knowledge_dir) / "testing" / f"{content_id}.md"
    assert markdown_path.exists()


@pytest.mark.asyncio
async def test_reconcile_detects_missing(sync_manager, sample_content_item):
    content_id = await sync_manager.write_content(sample_content_item, "reconcile-test")

    result = await sync_manager.reconcile()
    assert result["missing_markdown"] == 0
    assert result["missing_sqlite"] == 0
