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