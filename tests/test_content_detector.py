import pytest
from src.pipeline.content_detector import detect_content_type, extract_video_id


class TestDetectContentType:
    def test_youtube_url_standard_detected(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert detect_content_type(url) == "youtube"

    def test_youtube_short_url_detected(self):
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        assert detect_content_type(url) == "youtube"

    def test_youtube_be_url_detected(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert detect_content_type(url) == "youtube"

    def test_article_url_detected(self):
        url = "https://example.com/article"
        assert detect_content_type(url) == "article"

    def test_pdf_url_ending_detected(self):
        url = "https://example.com/document.pdf"
        assert detect_content_type(url) == "pdf"

    def test_raw_text_detected(self):
        text = "This is some raw text content that should be classified as text."
        assert detect_content_type(text) == "text"

    def test_multiline_text_detected(self):
        text = "This is line one.\nThis is line two.\nThis is line three."
        assert detect_content_type(text) == "text"

    def test_short_text_detected(self):
        text = "Short text"
        assert detect_content_type(text) == "text"


class TestExtractVideoId:
    def test_extract_video_id_standard(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_short(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_with_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=xxx&index=1"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_raises(self):
        url = "https://example.com/video"
        with pytest.raises(ValueError, match="Invalid YouTube URL"):
            extract_video_id(url)
