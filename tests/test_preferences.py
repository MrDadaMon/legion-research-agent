import pytest
from src.agent.handlers.preference_handler import detect_comparison


class TestComparisonDetection:
    def test_detect_prefer_over(self):
        result = detect_comparison("I prefer mean-reversion over momentum")
        assert result is not None
        assert result['preferred'] == 'mean-reversion'
        assert result['rejected'] == 'momentum'

    def test_detect_vs(self):
        result = detect_comparison("martingale vs grid trading")
        assert result is not None
        assert result['preferred'] == 'martingale'
        assert result['rejected'] == 'grid'

    def test_detect_no_comparison(self):
        result = detect_comparison("Tell me about trading bots")
        assert result is None


import pytest_asyncio
from src.agent.handlers.warning_handler import check_for_rejection_warnings, format_warning_message


class TestRejectionWarnings:
    @pytest_asyncio.fixture
    async def db_with_rejection(self, temp_db_path):
        from src.storage.database import Database
        db = Database(temp_db_path)
        await db._ensure_connection()
        await db.insert_preference(
            topic='trading',
            preference_type='reject',
            approach='martingale',
            reason='unlimited downside risk',
        )
        yield db
        await db.close()

    @pytest.mark.asyncio
    async def test_warning_fires_on_mention(self, db_with_rejection):
        warnings = await check_for_rejection_warnings(
            "I tried martingale but it failed",
            db_with_rejection
        )
        assert len(warnings) == 1
        assert 'martingale' in warnings[0]
        assert 'unlimited downside risk' in warnings[0]

    @pytest.mark.asyncio
    async def test_no_warning_for_non_rejected(self, db_with_rejection):
        warnings = await check_for_rejection_warnings(
            "I used mean-reversion for trading",
            db_with_rejection
        )
        assert len(warnings) == 0

    @pytest.mark.asyncio
    async def test_word_boundary_prevents_over_triggering(self, db_with_rejection):
        warnings = await check_for_rejection_warnings(
            "That was a smart decision",
            db_with_rejection
        )
        assert len(warnings) == 0

    def test_format_warning_message(self):
        msg = format_warning_message('martingale', 'unlimited risk', 'trading')
        assert 'martingale' in msg
        assert 'unlimited risk' in msg
        assert 'trading' in msg