import logging
from youtube_transcript_api import YouTubeTranscriptApi

from src.pipeline.content_detector import extract_video_id

logger = logging.getLogger(__name__)


async def extract_youtube(url: str) -> tuple[str, str, str]:
    video_id = extract_video_id(url)
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)
        raw_transcript = transcript.text
        title = f"YouTube Video {video_id}"
    except Exception as e:
        logger.warning(f"Could not retrieve transcript for video {video_id}: {e}")
        raw_transcript = "[Transcript unavailable - video may not have captions]"
        title = f"YouTube Video {video_id}"
    return (title, raw_transcript, video_id)
