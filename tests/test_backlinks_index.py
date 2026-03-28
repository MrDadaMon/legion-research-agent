import pytest
import tempfile
import os

from src.storage.backlinks_index import BacklinksIndex


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    index = BacklinksIndex(db_path)
    yield index
    import asyncio
    if index._conn:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(index._conn.close())
        loop.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_add_backlink(temp_db):
    await temp_db.add_backlink(source_id=1, target_id=2, link_text="related trading bot")
    backlinks = await temp_db.get_backlinks(target_id=2)
    assert len(backlinks) == 1
    assert backlinks[0].source_id == 1
    assert backlinks[0].link_text == "related trading bot"


@pytest.mark.asyncio
async def test_add_duplicate_backlink_is_ignored(temp_db):
    await temp_db.add_backlink(source_id=1, target_id=2, link_text="link")
    await temp_db.add_backlink(source_id=1, target_id=2, link_text="link")
    backlinks = await temp_db.get_backlinks(target_id=2)
    assert len(backlinks) == 1


@pytest.mark.asyncio
async def test_get_outgoing_links(temp_db):
    await temp_db.add_backlink(source_id=1, target_id=2, link_text="first")
    await temp_db.add_backlink(source_id=1, target_id=3, link_text="second")
    links = await temp_db.get_outgoing_links(source_id=1)
    assert len(links) == 2
    assert (2, "first") in links
    assert (3, "second") in links


@pytest.mark.asyncio
async def test_remove_backlinks_for_content(temp_db):
    await temp_db.add_backlink(source_id=1, target_id=2, link_text="link")
    await temp_db.add_backlink(source_id=2, target_id=3, link_text="another")
    await temp_db.remove_backlinks_for_content(content_id=2)
    backlinks = await temp_db.get_backlinks(target_id=2)
    assert len(backlinks) == 0
    outgoing = await temp_db.get_outgoing_links(source_id=2)
    assert len(outgoing) == 0


@pytest.mark.asyncio
async def test_get_linked_content_ids(temp_db):
    await temp_db.add_backlink(source_id=1, target_id=2, link_text="a")
    await temp_db.add_backlink(source_id=2, target_id=3, link_text="b")
    linked = await temp_db.get_linked_content_ids(content_id=2)
    assert set(linked) == {1, 3}


@pytest.mark.asyncio
async def test_backlink_with_context(temp_db):
    await temp_db.add_backlink(
        source_id=1,
        target_id=2,
        link_text="trading bot",
        context="This approach differs from the trading bot discussed in note 1.",
    )
    backlinks = await temp_db.get_backlinks(target_id=2)
    assert len(backlinks) == 1
    assert backlinks[0].context is not None
    assert "differs" in backlinks[0].context
