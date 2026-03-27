import pytest

from src.agent.handlers.summary_handler import (
    ask_question_mode,
    full_breakdown,
    quick_summary,
    save_for_later,
    show_summary_menu,
)
from src.models import ContentItem


@pytest.fixture
def sample_content():
    return ContentItem(
        id=1,
        source_type="youtube",
        source_url="https://youtube.com/watch?v=abc123",
        title="Test Video About AI",
        raw_content=(
            "Artificial intelligence is transforming how we work. "
            "Machine learning models can now write code, generate images, "
            "and answer complex questions. The future of AI is bright! "
            "Key applications include natural language processing and computer vision. "
            "Many companies are investing heavily in AI research. "
            "This is a revolutionary technology that changes everything. "
            "Some experts warn about potential risks from advanced AI systems."
        ),
        processed_date="2026-03-27T10:00:00",
        content_hash="abc123def456",
        reference_count=1,
    )


@pytest.fixture
def short_content():
    return ContentItem(
        id=2,
        source_type="text",
        source_url=None,
        title="Short Note",
        raw_content="AI is cool.",
        processed_date="2026-03-27T10:00:00",
        content_hash="short123",
        reference_count=1,
    )


@pytest.fixture
def mock_db(sample_content, short_content):
    class MockDB:
        def __init__(self, content):
            self._content = content

        async def get_content(self, content_id):
            if content_id == 1:
                return sample_content
            if content_id == 2:
                return short_content
            return None

    return MockDB(sample_content)


@pytest.mark.asyncio
async def test_quick_summary_returns_3_to_5_bullets(mock_db):
    result = await quick_summary(1, mock_db)
    lines = result.strip().split("\n")
    bullet_lines = [l for l in lines if l.startswith("- ")]
    assert len(bullet_lines) >= 3
    assert len(bullet_lines) <= 5


@pytest.mark.asyncio
async def test_quick_summary_short_content_returns_raw(short_content):
    class ShortDB:
        async def get_content(self, content_id):
            return short_content

    result = await quick_summary(2, ShortDB())
    assert "AI is cool" in result


@pytest.mark.asyncio
async def test_full_breakdown_includes_key_moments(mock_db):
    result = await full_breakdown(1, mock_db)
    assert "## Key Moments" in result


@pytest.mark.asyncio
async def test_full_breakdown_includes_follow_up_questions(mock_db):
    result = await full_breakdown(1, mock_db)
    assert "## Follow-up Questions" in result
    lines = result.strip().split("\n")
    question_lines = [l for l in lines if l.startswith("- What")]
    assert len(question_lines) >= 2


@pytest.mark.asyncio
async def test_ask_question_mode_finds_relevant_sentences(mock_db):
    result = await ask_question_mode(1, mock_db, "What about machine learning?")
    assert "Based on the content:" in result


@pytest.mark.asyncio
async def test_ask_question_mode_returns_fallback_when_no_match(mock_db):
    result = await ask_question_mode(1, mock_db, "xyzzy plover")
    assert "couldn't find" in result.lower()


@pytest.mark.asyncio
async def test_save_for_later_returns_confirmation(mock_db):
    result = await save_for_later(1, mock_db)
    assert "Saved for later" in result
    assert "Test Video About AI" in result


@pytest.mark.asyncio
async def test_show_summary_menu_returns_selection(monkeypatch):
    from src.agent.handlers import summary_handler

    class MockSelector:
        async def ask_async(self):
            return "Quick Summary"

    def mock_select(*args, **kwargs):
        return MockSelector()

    mock_questionary = type("MockQ", (), {"select": mock_select})()
    monkeypatch.setattr(summary_handler, "questionary", mock_questionary)
    result = await show_summary_menu(1, "Test Title")
    assert result == "Quick Summary"
