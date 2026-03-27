import pytest
from datetime import datetime, timedelta
from src.agent.handlers.gap_handler import (
    should_suggest_gap,
    identify_gaps_from_content,
    generate_gap_research,
    GAP_CONTENT_THRESHOLD,
    GAP_IDLE_HOURS,
    GAP_COOLDOWN_DAYS,
)
from src.models.content import ContentItem


class TestGapConstants:
    def test_content_threshold(self):
        assert GAP_CONTENT_THRESHOLD == 3

    def test_idle_hours(self):
        assert GAP_IDLE_HOURS == 24

    def test_cooldown_days(self):
        assert GAP_COOLDOWN_DAYS == 7


class TestShouldSuggestGap:
    def test_no_metadata_returns_false(self):
        should, reason = should_suggest_gap(None)
        assert should is False

    def test_below_content_threshold(self):
        metadata = {
            'content_count': 2,
            'last_content_date': (datetime.now() - timedelta(hours=48)).isoformat(),
        }
        should, reason = should_suggest_gap(metadata)
        assert should is False
        assert '2' in reason

    def test_below_idle_threshold(self):
        metadata = {
            'content_count': 5,
            'last_content_date': (datetime.now() - timedelta(hours=12)).isoformat(),
        }
        should, reason = should_suggest_gap(metadata)
        assert should is False
        assert '12' in reason

    def test_within_cooldown(self):
        metadata = {
            'content_count': 5,
            'last_content_date': (datetime.now() - timedelta(hours=48)).isoformat(),
            'last_gap_suggestion': (datetime.now() - timedelta(days=3)).isoformat(),
        }
        should, reason = should_suggest_gap(metadata)
        assert should is False
        assert 'cooldown' in reason.lower()

    def test_ready_for_gap_suggestion(self):
        metadata = {
            'content_count': 5,
            'last_content_date': (datetime.now() - timedelta(hours=48)).isoformat(),
            'last_gap_suggestion': (datetime.now() - timedelta(days=10)).isoformat(),
        }
        should, reason = should_suggest_gap(metadata)
        assert should is True
        assert 'ready' in reason.lower()

    def test_never_suggested_before(self):
        metadata = {
            'content_count': 5,
            'last_content_date': (datetime.now() - timedelta(hours=48)).isoformat(),
            'last_gap_suggestion': None,
        }
        should, reason = should_suggest_gap(metadata)
        assert should is True


class TestIdentifyGapsFromContent:
    def test_finds_missing_subtopics(self):
        content = [
            ContentItem(
                id=1,
                source_type='article',
                source_url='https://example.com/1',
                title='Trading Strategies',
                raw_content='This article covers momentum and mean reversion strategies.',
                processed_date='2026-03-26T12:00:00',
                content_hash='abc',
                reference_count=1,
            ),
        ]

        gaps = identify_gaps_from_content('trading', content)

        # Should find common trading subtopics NOT in the content
        assert 'risk management' in gaps
        assert 'backtesting' in gaps
        assert 'position sizing' in gaps

    def test_excludes_mentioned_subtopics(self):
        content = [
            ContentItem(
                id=1,
                source_type='article',
                source_url='https://example.com/1',
                title='Risk Management Guide',
                raw_content='This article covers risk management and position sizing extensively.',
                processed_date='2026-03-26T12:00:00',
                content_hash='abc',
                reference_count=1,
            ),
        ]

        gaps = identify_gaps_from_content('trading', content)

        # risk management and position sizing should NOT be in gaps
        assert 'risk management' not in gaps
        assert 'position sizing' not in gaps


class TestGenerateGapResearch:
    def test_generates_gaps_for_aspect(self):
        answers = {
            'aspect': 'Risk Management',
            'specific': None,
        }

        gaps = generate_gap_research('Trading', answers)

        assert len(gaps) >= 2
        assert any('position' in g['title'].lower() for g in gaps)

    def test_adds_specific_question(self):
        answers = {
            'aspect': 'General',
            'specific': 'How do I handle drawdowns?',
        }

        gaps = generate_gap_research('Trading', answers)

        assert len(gaps) >= 1
        assert 'drawdowns' in gaps[0]['title'].lower()
        assert 'How do I handle drawdowns?' in gaps[0]['search_query']

    def test_limits_to_5_gaps(self):
        answers = {
            'aspect': 'General',
            'specific': 'What about everything?',
        }

        gaps = generate_gap_research('Trading', answers)

        assert len(gaps) <= 5
