import pytest
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
