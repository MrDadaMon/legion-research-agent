import pytest
from src.agent.handlers.ytdlp_search_handler import (
    is_youtube_search_query,
    extract_youtube_search_topic,
    format_youtube_results,
    YouTubeVideo,
)


class TestYouTubeSearchDetection:
    def test_find_videos_on(self):
        assert is_youtube_search_query("find videos on trading bots")
        assert is_youtube_search_query("find video on Python tutorials")

    def test_search_youtube_patterns(self):
        assert is_youtube_search_query("search YouTube for crypto trading strategies")
        assert is_youtube_search_query("search youtube for machine learning")

    def test_whats_on_youtube_patterns(self):
        assert is_youtube_search_query("what's on YouTube about trading")
        assert is_youtube_search_query("what is on youtube about peptides")

    def test_recommend_videos_patterns(self):
        assert is_youtube_search_query("recommend me some videos on trading")
        assert is_youtube_search_query("recommend videos about crypto")

    def test_negative_cases(self):
        assert not is_youtube_search_query("find me more like this on trading")
        assert not is_youtube_search_query("search for more on crypto")
        assert not is_youtube_search_query("what do I have on trading bots")

    def test_case_insensitive(self):
        assert is_youtube_search_query("FIND VIDEOS ON PYTHON")
        assert is_youtube_search_query("Search YouTube for something")


class TestExtractSearchTopic:
    def test_find_videos_on(self):
        topic = extract_youtube_search_topic("find videos on trading bots")
        assert topic == "trading bots"

    def test_search_youtube_for(self):
        topic = extract_youtube_search_topic("search YouTube for crypto trading")
        assert topic == "crypto trading"

    def test_whats_on_youtube(self):
        topic = extract_youtube_search_topic("what's on YouTube about machine learning")
        assert topic == "machine learning"

    def test_recommend_videos(self):
        topic = extract_youtube_search_topic("recommend me some videos on trading strategies")
        assert topic == "trading strategies"

    def test_with_question_mark(self):
        topic = extract_youtube_search_topic("find videos on trading bots?")
        assert topic == "trading bots"

    def test_no_topic_found(self):
        topic = extract_youtube_search_topic("regular conversation text")
        assert topic is None


class TestYouTubeVideo:
    def test_formatted_basic(self):
        video = YouTubeVideo(
            title="Test Video",
            url="https://youtube.com/watch?v=abc",
            uploader="Test Channel",
            view_count=None,
            subscriber_count=None,
            duration=None,
            upload_date=None,
            views_per_sub=None,
        )
        formatted = video.formatted()
        assert "Test Video" in formatted
        assert "Test Channel" in formatted
        assert "https://youtube.com/watch?v=abc" in formatted

    def test_formatted_with_views_and_quality(self):
        video = YouTubeVideo(
            title="Popular Video",
            url="https://youtube.com/watch?v=xyz",
            uploader="Big Channel",
            view_count=1_500_000,
            subscriber_count=50_000,
            duration=None,
            upload_date=None,
            views_per_sub=30.0,
        )
        formatted = video.formatted()
        assert "1.5M" in formatted
        assert "50.0K" in formatted
        assert "30.0x" in formatted

    def test_formatted_with_duration(self):
        video = YouTubeVideo(
            title="Long Video",
            url="https://youtube.com/watch?v=long",
            uploader="Channel",
            view_count=None,
            subscriber_count=None,
            duration="1:30:00",
            upload_date=None,
            views_per_sub=None,
        )
        formatted = video.formatted()
        assert "1:30:00" in formatted

    def test_format_views(self):
        assert YouTubeVideo._format_views(500) == "500"
        assert YouTubeVideo._format_views(1500) == "1.5K"
        assert YouTubeVideo._format_views(1_500_000) == "1.5M"

    def test_format_subs(self):
        assert YouTubeVideo._format_subs(500) == "500"
        assert YouTubeVideo._format_subs(1500) == "1.5K"
        assert YouTubeVideo._format_subs(1_500_000) == "1.5M"

    def test_format_date(self):
        assert YouTubeVideo._format_date("20260327") == "2026-03-27"


class TestFormatYoutubeResults:
    def test_empty_results_with_date_filter(self):
        result = format_youtube_results([], "trading bots", months=6)
        assert "No results found" in result
        assert "trading bots" in result
        assert "last 6 months" in result

    def test_empty_results_no_date_filter(self):
        result = format_youtube_results([], "trading bots", months=0)
        assert "No results found" in result
        assert "trading bots" in result
        assert "last 6 months" not in result

    def test_single_result(self):
        video = YouTubeVideo(
            title="Test Video",
            url="https://youtube.com/watch?v=abc",
            uploader="Test Channel",
            view_count=1000,
            subscriber_count=None,
            duration="10:00",
            upload_date="20260327",
            views_per_sub=None,
        )
        result = format_youtube_results([video], "test query")
        assert "Test Video" in result
        assert "Test Channel" in result
        assert "1.0K" in result
        assert "10:00" in result
        assert "quality" in result.lower()

    def test_multiple_results(self):
        videos = [
            YouTubeVideo("Video 1", "https://yt1.com", "Channel 1", 1000, None, "5:00", "20260327", None),
            YouTubeVideo("Video 2", "https://yt2.com", "Channel 2", 2000, None, "10:00", "20260326", None),
        ]
        result = format_youtube_results(videos, "test")
        assert "2 video(s)" in result
        assert "Video 1" in result
        assert "Video 2" in result
