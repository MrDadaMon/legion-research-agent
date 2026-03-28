import pytest
from src.storage.database import Database


@pytest.mark.asyncio
async def test_insert_research_session(temp_db_path):
    db = Database(temp_db_path)
    await db._ensure_connection()
    session_id = await db.insert_research_session(
        query="trading bot strategies",
        results_count=5,
    )
    assert session_id > 0
    await db.close()


@pytest.mark.asyncio
async def test_insert_with_seed_content(temp_db_path, sample_content_item):
    db = Database(temp_db_path)
    await db._ensure_connection()

    content_id = await db.insert_content(sample_content_item)

    session_id = await db.insert_research_session(
        query="more on trading bots",
        seed_content_id=content_id,
        results_count=3,
    )

    sessions = await db.get_recent_sessions(limit=1)
    assert sessions[0]["seed_content_id"] == content_id
    assert sessions[0]["seed_content_title"] == sample_content_item.title
    await db.close()


@pytest.mark.asyncio
async def test_update_research_session(temp_db_path):
    db = Database(temp_db_path)
    await db._ensure_connection()

    await db.insert_research_session(
        query="initial query",
        results_count=0,
    )

    sessions = await db.get_recent_sessions(limit=1)
    session_id = sessions[0]["id"]

    await db.update_research_session(
        session_id,
        results_count=10,
        deliverable_types="podcast,infographic",
    )

    sessions = await db.get_recent_sessions(limit=1)
    assert sessions[0]["results_count"] == 10
    assert "podcast" in sessions[0]["deliverable_types"]
    await db.close()


@pytest.mark.asyncio
async def test_get_recent_sessions(temp_db_path):
    db = Database(temp_db_path)
    await db._ensure_connection()

    for i in range(5):
        await db.insert_research_session(query=f"recent-test-query", results_count=i)

    sessions = await db.get_recent_sessions(limit=3)
    assert len(sessions) == 3
    # All should have the same query (order-independent check)
    assert all(s["query"] == "recent-test-query" for s in sessions)
    await db.close()


@pytest.mark.asyncio
async def test_get_session_history_filtered(temp_db_path):
    db = Database(temp_db_path)
    await db._ensure_connection()

    await db.insert_research_session(query="trading bots crypto", results_count=1)
    await db.insert_research_session(query="cooking recipes", results_count=2)
    await db.insert_research_session(query="crypto trading strategies", results_count=3)

    sessions = await db.get_session_history(topic="trading")
    assert len(sessions) == 2
    queries = [s["query"] for s in sessions]
    assert "trading bots crypto" in queries
    assert "crypto trading strategies" in queries
    await db.close()


@pytest.mark.asyncio
async def test_session_with_deliverables(temp_db_path):
    db = Database(temp_db_path)
    await db._ensure_connection()

    await db.insert_research_session(
        query="research on peptides",
        results_count=5,
        deliverable_types="podcast,flashcards",
    )

    sessions = await db.get_recent_sessions(limit=1)
    assert "podcast" in sessions[0]["deliverable_types"]
    assert "flashcards" in sessions[0]["deliverable_types"]
    await db.close()
