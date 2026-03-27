import pytest
from src.agent.handlers.conflict_handler import (
    extract_key_points,
    find_disagreements,
    OPPOSING_PAIRS,
)


class TestExtractKeyPoints:
    def test_extracts_sentences(self):
        content = "This is the first sentence. This is the second. This is the third."
        points = extract_key_points(content)
        assert len(points) == 3
        assert "first sentence" in points[0]

    def test_respects_limit(self):
        content = "One. Two. Three. Four. Five."
        points = extract_key_points(content, num_points=2)
        assert len(points) == 2

    def test_handles_empty(self):
        points = extract_key_points("")
        assert points == []


class TestFindDisagreements:
    def test_finds_opposing_pairs(self):
        summary_a = ["This approach is bad for trading"]
        summary_b = ["This approach is good for trading"]

        disagreements = find_disagreements(summary_a, summary_b)

        assert len(disagreements) >= 1
        # Should find "bad" vs "good"
        types = [d['type'] for d in disagreements]
        assert any('bad' in t and 'good' in t for t in types)

    def test_no_disagreement_on_neutral(self):
        summary_a = ["This is about trading strategies"]
        summary_b = ["This is about cooking recipes"]

        disagreements = find_disagreements(summary_a, summary_b)
        assert len(disagreements) == 0

    def test_finds_multiple_disagreements(self):
        summary_a = ["This approach is bad and always fails"]
        summary_b = ["This approach is good and always succeeds"]

        disagreements = find_disagreements(summary_a, summary_b)
        # Should find at least bad/good and fail/succeed
        assert len(disagreements) >= 2

    def test_opposing_pairs_complete(self):
        """Verify OPPOSING_PAIRS contains expected pairs."""
        pair_words = set()
        for pos, neg in OPPOSING_PAIRS:
            pair_words.add(pos)
            pair_words.add(neg)

        # Check some expected pairs are present
        assert 'not' in pair_words
        assert 'do' in pair_words
        assert 'never' in pair_words
        assert 'always' in pair_words