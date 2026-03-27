import pytest
import asyncio
from src.storage.database import Database
from src.models import ContentItem, compute_content_hash


@pytest.mark.asyncio
async def test_insert_content_returns_id(temp_db_path, sample_content_item):
    db = Database(temp_db_path)
    content_id = await db.insert_content(sample_content_item)
    assert content_id is not None
    assert content_id > 0
    await db.close()


@pytest.mark.asyncio
async def test_duplicate_hash_increments_reference_count(temp_db_path, sample_content_item):
    db = Database(temp_db_path)
    id1 = await db.insert_content(sample_content_item)
    id2 = await db.insert_content(sample_content_item)
    assert id1 == id2

    content = await db.get_content(id1)
    assert content is not None
    assert content.reference_count == 2
    await db.close()


@pytest.mark.asyncio
async def test_get_content(temp_db_path, sample_content_item):
    db = Database(temp_db_path)
    inserted_id = await db.insert_content(sample_content_item)

    content = await db.get_content(inserted_id)
    assert content is not None
    assert content.title == "Test Article"
    assert content.source_type == "article"
    assert content.source_url == "https://example.com/article"
    await db.close()


@pytest.mark.asyncio
async def test_content_exists_by_hash(temp_db_path, sample_content_item):
    db = Database(temp_db_path)
    await db.insert_content(sample_content_item)

    exists = await db.content_exists_by_hash(sample_content_item.content_hash)
    assert exists is True

    exists_false = await db.content_exists_by_hash("nonexistent_hash")
    assert exists_false is False
    await db.close()


@pytest.mark.asyncio
async def test_get_or_create_topic(temp_db_path):
    db = Database(temp_db_path)
    id1, slug1 = await db.get_or_create_topic("Artificial Intelligence")
    assert id1 is not None
    assert slug1 == "artificial-intelligence"

    id2, slug2 = await db.get_or_create_topic("Artificial Intelligence")
    assert id1 == id2
    assert slug2 == "artificial-intelligence"

    id3, slug3 = await db.get_or_create_topic("Machine Learning")
    assert id3 != id1
    assert slug3 == "machine-learning"
    await db.close()


@pytest.mark.asyncio
async def test_link_content_to_topic(temp_db_path, sample_content_item):
    db = Database(temp_db_path)
    content_id = await db.insert_content(sample_content_item)
    topic_id, topic_slug = await db.get_or_create_topic("Tech")

    await db.link_content_to_topic(content_id, topic_id)

    topics = await db.get_content_topics(content_id)
    assert topic_slug in topics
    await db.close()


@pytest.mark.asyncio
async def test_get_all_content(temp_db_path, sample_content_item):
    db = Database(temp_db_path)
    await db.insert_content(sample_content_item)

    item2 = ContentItem(
        id=None,
        source_type="youtube",
        source_url="https://youtube.com/watch?v=abc",
        title="Test Video",
        raw_content="Video transcript content.",
        processed_date="2026-03-26T13:00:00",
        content_hash=compute_content_hash("Video transcript content."),
        reference_count=1,
    )
    await db.insert_content(item2)

    all_content = await db.get_all_content()
    assert len(all_content) == 2
    await db.close()


@pytest.mark.asyncio
async def test_get_topic_content(temp_db_path, sample_content_item):
    db = Database(temp_db_path)
    content_id = await db.insert_content(sample_content_item)
    topic_id, topic_slug = await db.get_or_create_topic("Science")
    await db.link_content_to_topic(content_id, topic_id)

    content_list = await db.get_topic_content(topic_slug)
    assert len(content_list) == 1
    assert content_list[0].title == "Test Article"
    await db.close()
