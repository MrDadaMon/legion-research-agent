import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.storage.obsidian_store import ObsidianStore, ObsidianNote, slugify_for_obsidian
from src.models import ContentItem


@pytest.fixture
def temp_vault():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ObsidianStore(vault_path=str(Path(tmpdir) / "vault"))
        yield store


@pytest.fixture
def sample_content():
    return ContentItem(
        id=1,
        source_type="youtube",
        source_url="https://youtube.com/watch?v=abc123",
        title="Trading Bot Strategies",
        raw_content="Here are the key strategies for building trading bots...",
        processed_date=datetime.now().isoformat(),
        content_hash="abc123hash",
    )


def test_slugify():
    assert slugify_for_obsidian("Trading Bot Strategies") == "trading-bot-strategies"
    assert slugify_for_obsidian("What's This?") == "what-s-this"
    assert slugify_for_obsidian("  Spaces  ") == "spaces"
    assert slugify_for_obsidian("UPPERCASE") == "uppercase"


def test_obsidian_note_frontmatter(sample_content):
    note = ObsidianNote(
        item=sample_content,
        topic_slug="trading",
        tags=["trading", "bots", "finance"],
        related_ids=[2, 3],
        related_titles={2: "Risk Management", 3: "Crypto Trading"},
    )
    fm = note.to_yaml_frontmatter()
    assert "id: 1" in fm
    assert "title: Trading Bot Strategies" in fm
    assert "source_type: youtube" in fm
    assert "topic: trading" in fm
    assert "tags:" in fm
    assert "- trading" in fm
    assert "- bots" in fm


def test_obsidian_note_body_with_links(sample_content):
    note = ObsidianNote(
        item=sample_content,
        topic_slug="trading",
        tags=["trading"],
        related_ids=[2],
        related_titles={2: "Risk Management"},
    )
    body = note.to_markdown_body()
    assert "# Trading Bot Strategies" in body
    assert "[[risk-management-2|Risk Management]]" in body
    assert "[[trading-bot-strategies-1|Risk Management]]" not in body


def test_obsidian_note_full_string(sample_content):
    note = ObsidianNote(item=sample_content, topic_slug="trading", tags=["trading"])
    full = note.to_string()
    assert full.startswith("---")
    assert "# Trading Bot Strategies" in full
    assert "## Content" in full


@pytest.mark.asyncio
async def test_save_content_note(temp_vault, sample_content):
    path = await temp_vault.save(
        item=sample_content,
        topic_slug="trading",
        tags=["trading", "bots"],
        related_ids=[2],
        related_titles={2: "Risk Management"},
    )
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Trading Bot Strategies" in content
    assert "[[risk-management-2|Risk Management]]" in content
    assert "source_type: youtube" in content


@pytest.mark.asyncio
async def test_create_topic_index(temp_vault):
    items = [
        ContentItem(id=1, source_type="video", source_url="", title="First Video",
                    raw_content="Content", processed_date="", content_hash="h1"),
        ContentItem(id=2, source_type="article", source_url="", title="Second Article",
                    raw_content="Content", processed_date="", content_hash="h2"),
    ]
    path = await temp_vault.create_topic_index(
        topic_slug="trading",
        topic_name="Trading",
        content_items=items,
    )
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "# Trading" in content
    assert "First Video" in content
    assert "Second Article" in content
    assert "[[first-video-1|First Video]]" in content
    assert "[[second-article-2|Second Article]]" in content


@pytest.mark.asyncio
async def test_create_daily_session(temp_vault):
    path = await temp_vault.create_daily_session(
        date_str="2026-03-27",
        summary="Researched trading bot strategies",
        content_ids=[1, 2, 3],
        research_query="trading bot strategies",
    )
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Research Session: 2026-03-27" in content
    assert "trading bot strategies" in content
    assert "Researched trading bot strategies" in content
    assert "Note 1" in content
    assert "Note 2" in content
    assert "Note 3" in content


@pytest.mark.asyncio
async def test_append_to_daily_session(temp_vault):
    await temp_vault.create_daily_session(date_str="2026-03-27", summary="First entry")
    path = await temp_vault.append_to_daily_session(
        entry="Added more notes on risk management",
        date_str="2026-03-27",
    )
    content = path.read_text(encoding="utf-8")
    assert "First entry" in content
    assert "Added more notes" in content


@pytest.mark.asyncio
async def test_list_topics(temp_vault):
    await temp_vault.create_topic_index("trading", "Trading", [])
    await temp_vault.create_topic_index("crypto", "Crypto", [])
    topics = await temp_vault.list_topics()
    assert set(topics) == {"trading", "crypto"}


@pytest.mark.asyncio
async def test_list_session_files_sorted(temp_vault):
    await temp_vault.create_daily_session(date_str="2026-03-25")
    await temp_vault.create_daily_session(date_str="2026-03-27")
    await temp_vault.create_daily_session(date_str="2026-03-26")
    sessions = await temp_vault.list_session_files()
    dates = [s.stem for s in sessions]
    assert dates == ["2026-03-25", "2026-03-26", "2026-03-27"]


@pytest.mark.asyncio
async def test_delete_content(temp_vault, sample_content):
    await temp_vault.save(sample_content, topic_slug="trading")
    deleted = await temp_vault.delete("trading", sample_content.id, sample_content.title)
    assert deleted
    assert not temp_vault._content_path("trading", sample_content.id, sample_content.title).exists()
