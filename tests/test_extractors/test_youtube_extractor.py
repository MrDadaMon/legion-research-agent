import pytest
from unittest.mock import patch, MagicMock


class TestYouTubeExtractor:
    @pytest.mark.asyncio
    async def test_extract_youtube_success(self):
        mock_transcript = MagicMock()
        mock_transcript.text = "Hello world"

        with patch(
            "youtube_transcript_api.YouTubeTranscriptApi.fetch",
            return_value=mock_transcript,
        ):
            from src.pipeline.extractors.youtube_extractor import extract_youtube
            title, raw_content, video_id = await extract_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )
            assert video_id == "dQw4w9WgXcQ"
            assert raw_content == "Hello world"
            assert "dQw4w9WgXcQ" in title

    @pytest.mark.asyncio
    async def test_extract_youtube_transcript_unavailable(self):
        with patch(
            "youtube_transcript_api.YouTubeTranscriptApi.fetch",
            side_effect=Exception("Transcript unavailable"),
        ):
            from src.pipeline.extractors.youtube_extractor import extract_youtube
            title, raw_content, video_id = await extract_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )
            assert video_id == "dQw4w9WgXcQ"
            assert "[Transcript unavailable" in raw_content

    @pytest.mark.asyncio
    async def test_extract_youtube_invalid_url(self):
        with pytest.raises(ValueError, match="Invalid YouTube URL"):
            from src.pipeline.extractors.youtube_extractor import extract_youtube
            await extract_youtube("https://example.com/video")
