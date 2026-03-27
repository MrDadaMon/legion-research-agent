import pytest
import pytest_asyncio
from src.agent.handlers.surfacing_handler import (
    is_surface_query,
    extract_surface_topic,
    format_surfaced_item,
)
from src.models.content import ContentItem


class TestSurfaceQueryDetection:
    def test_is_surface_query_what_do_i_have_on(self):
        assert is_surface_query("what do I have on trading bots?") is True

    def test_is_surface_query_what_do_i_know_about(self):
        assert is_surface_query("what do I know about trading?") is True

    def test_is_surface_query_show_me_content(self):
        assert is_surface_query("show me content about trading") is True

    def test_is_surface_query_negative(self):
        assert is_surface_query("I prefer mean-reversion over momentum") is False
        assert is_surface_query("Tell me about my day") is False

    def test_extract_surface_topic(self):
        topic = extract_surface_topic("what do I have on trading bots?")
        assert topic == "trading bots"

        topic = extract_surface_topic("show me content about crypto")
        assert topic == "crypto"


class TestSurfacingFormat:
    def test_format_surfaced_item(self):
        content = ContentItem(
            id=1,
            source_type='article',
            source_url='https://example.com/article',
            title='Trading Bot Strategies',
            raw_content='This article discusses various trading bot strategies including martingale, mean-reversion, and momentum approaches.',
            processed_date='2026-03-26T12:00:00',
            content_hash='abc123',
            reference_count=1,
        )
        matched_on = ['topic: trading-bots', 'title: Trading Bot']

        result = format_surfaced_item(content, matched_on)

        assert 'Trading Bot Strategies' in result
        assert 'https://example.com/article' in result
        assert '2026-03-26' in result
        assert 'topic: trading-bots' in result
        assert 'Summary:' in result
        assert 'trading bot strategies' in result.lower()

    def test_format_surfaced_item_no_url(self):
        content = ContentItem(
            id=2,
            source_type='text',
            source_url=None,
            title='My Notes',
            raw_content='These are my notes about trading.',
            processed_date='2026-03-25T10:00:00',
            content_hash='def456',
            reference_count=1,
        )

        result = format_surfaced_item(content, ['title: My Notes'])

        assert 'My Notes' in result
        assert 'text' in result  # Falls back to source_type
        assert '2026-03-25' in result


class TestSurfacingIntegration:
    @pytest_asyncio.fixture
    async def db_with_content(self, temp_db_path):
        from src.storage.database import Database
        from src.models.content import ContentItem, compute_content_hash

        db = Database(temp_db_path)
        await db._ensure_connection()

        # Insert test content
        items = [
            ContentItem(
                id=None,
                source_type='article',
                source_url='https://example.com/trading',
                title='Trading Bot Strategies',
                raw_content='This article covers trading bot strategies including mean-reversion and momentum.',
                processed_date='2026-03-26T12:00:00',
                content_hash=compute_content_hash('trading content 1'),
                reference_count=1,
            ),
            ContentItem(
                id=None,
                source_type='article',
                source_url='https://example.com/crypto',
                title='Cryptocurrency Trading',
                raw_content='This article is about cryptocurrency and blockchain trading.',
                processed_date='2026-03-25T12:00:00',
                content_hash=compute_content_hash('trading content 2'),
                reference_count=1,
            ),
        ]

        for item in items:
            content_id = await db.insert_content(item)
            topic_id, topic_slug = await db.get_or_create_topic('trading')
            await db.link_content_to_topic(content_id, topic_id)

        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_surface_content_finds_topic_match(self, db_with_content):
        from src.agent.handlers.surfacing_handler import surface_content
        results = await surface_content('trading', db_with_content, limit=5)
        assert len(results) >= 1
        # Should find content with 'trading' in title or topic
        titles = [r['content'].title for r in results]
        assert any('trading' in t.lower() for t in titles)

    @pytest.mark.asyncio
    async def test_surface_content_includes_metadata(self, db_with_content):
        from src.agent.handlers.surfacing_handler import surface_content
        results = await surface_content('trading', db_with_content, limit=5)
        assert len(results) >= 1

        # Each result should have score and matched_on
        for r in results:
            assert hasattr(r['content'], 'source_url')
            assert hasattr(r['content'], 'processed_date')
            assert hasattr(r['content'], 'raw_content')
            assert 'score' in r
            assert 'matched_on' in r

    @pytest.mark.asyncio
    async def test_surface_content_no_match(self, db_with_content):
        from src.agent.handlers.surfacing_handler import surface_content
        results = await surface_content('cooking recipes', db_with_content, limit=5)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_surface_content_limit(self, db_with_content):
        from src.agent.handlers.surfacing_handler import surface_content
        from src.models.content import ContentItem, compute_content_hash
        # Add more content
        for i in range(10):
            item = ContentItem(
                id=None,
                source_type='article',
                source_url=f'https://example.com/test{i}',
                title=f'Test Article {i}',
                raw_content=f'Test content {i}',
                processed_date='2026-03-26T12:00:00',
                content_hash=compute_content_hash(f'test content {i}'),
                reference_count=1,
            )
            await db_with_content.insert_content(item)

        results = await surface_content('test', db_with_content, limit=3)
        assert len(results) == 3  # Limited to 3
