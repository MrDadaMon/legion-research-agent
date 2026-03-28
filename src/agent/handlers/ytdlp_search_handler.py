import re
import subprocess
import json
import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)

YTDLP_SEARCH_TRIGGER_PATTERNS = [
    r"find\s+videos?\s+on",
    r"search\s+youtube\s+(?:for\s+)?",
    r"find\s+(?:me\s+)?(?:some\s+)?(?:good\s+)?(?:videos?|youtube)\s+(?:on|about)",
    r"what(?:\s*'s|\s+is|\s+on)?\s+(?:on|in)\s+youtube\s+(?:about|on)",
    r"youtube\s+search\s+(?:for\s+)?",
    r"look\s+up\s+(?:videos?|youtube)\s+(?:on|about)",
    r"recommend\s+(?:me\s+)?(?:some\s+)?(?:videos?|youtube)\s+(?:on|about)",
]


class YouTubeVideo(NamedTuple):
    title: str
    url: str
    uploader: str
    view_count: int | None
    duration: str | None
    upload_date: str | None

    def formatted(self) -> str:
        parts = [f"**{self.title}**"]
        parts.append(f"  Channel: {self.uploader}")
        if self.view_count:
            parts.append(f"  Views: {self._format_views(self.view_count)}")
        if self.duration:
            parts.append(f"  Duration: {self.duration}")
        if self.upload_date:
            parts.append(f"  Uploaded: {self._format_date(self.upload_date)}")
        parts.append(f"  URL: {self.url}")
        return "\n".join(parts)

    @staticmethod
    def _format_views(count: int) -> str:
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        if count >= 1_000:
            return f"{count / 1_000:.1f}K"
        return str(count)

    @staticmethod
    def _format_date(date_str: str) -> str:
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str


def is_youtube_search_query(user_message: str) -> bool:
    """Detect if user wants YouTube search.

    Examples: "find videos on trading bots", "search YouTube for Python",
              "what's on YouTube about crypto"
    """
    user_lower = user_message.lower().strip()
    for pattern in YTDLP_SEARCH_TRIGGER_PATTERNS:
        if re.search(pattern, user_lower):
            return True
    return False


def extract_youtube_search_topic(user_message: str) -> str | None:
    """Extract the search topic from a YouTube search query.

    E.g. "find videos on trading bots" -> "trading bots"
    """
    user_lower = user_message.lower().strip()

    patterns = [
        r'find\s+videos?\s+on\s+(.+?)(?:\?|$)',
        r'search\s+youtube\s+(?:for\s+)?(.+?)(?:\?|$)',
        r'find\s+(?:me\s+)?(?:some\s+)?(?:good\s+)?(?:videos?|youtube)\s+(?:on|about)\s+(.+?)(?:\?|$)',
        r"what(?:'s)?(?:\s+is)?\s+on\s+youtube\s+about\s+(.+?)(?:\?|$)",
        r'youtube\s+search\s+(?:for\s+)?(.+?)(?:\?|$)',
        r'look\s+up\s+(?:videos?|youtube)\s+(?:on|about)\s+(.+?)(?:\?|$)',
        r'recommend\s+(?:me\s+)?(?:some\s+)?(?:videos?|youtube)\s+(?:on|about)\s+(.+?)(?:\?|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, user_lower)
        if match:
            topic = match.group(1).strip()
            if topic and len(topic) > 1:
                return topic
    return None


def search_youtube(query: str, max_results: int = 10) -> list[YouTubeVideo]:
    """Search YouTube using yt-dlp and return metadata for top results.

    Uses yt-dlp's search functionality to find videos matching query.
    Returns metadata only (no download).

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 10)

    Returns:
        List of YouTubeVideo namedtuples with metadata
    """
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            f'ytsearch{max_results}:{query}',
            '--flat-playlist',
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.warning(f"yt-dlp search failed: {result.stderr}")
            return []

        videos = []
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                video = _parse_video_data(data)
                if video:
                    videos.append(video)
            except json.JSONDecodeError:
                continue

        return videos

    except subprocess.TimeoutExpired:
        logger.warning(f"yt-dlp search timed out for query: {query}")
        return []
    except FileNotFoundError:
        logger.error("yt-dlp not found in PATH")
        return []
    except Exception as e:
        logger.error(f"yt-dlp search error: {e}")
        return []


def get_video_metadata(url: str) -> YouTubeVideo | None:
    """Get metadata for a single YouTube video URL.

    Args:
        url: YouTube video URL

    Returns:
        YouTubeVideo namedtuple or None if failed
    """
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            url,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.warning(f"yt-dlp metadata failed for {url}: {result.stderr}")
            return None

        data = json.loads(result.stdout.strip())
        return _parse_video_data(data)

    except subprocess.TimeoutExpired:
        logger.warning(f"yt-dlp metadata timed out for {url}")
        return None
    except FileNotFoundError:
        logger.error("yt-dlp not found in PATH")
        return None
    except Exception as e:
        logger.error(f"yt-dlp metadata error for {url}: {e}")
        return None


def _parse_video_data(data: dict) -> YouTubeVideo | None:
    """Parse yt-dlp JSON data into YouTubeVideo namedtuple."""
    try:
        title = data.get('title', 'Unknown Title')
        url = data.get('webpage_url', data.get('url', ''))
        uploader = data.get('uploader', data.get('channel', 'Unknown Channel'))
        view_count = data.get('view_count')
        duration_seconds = data.get('duration')

        if duration_seconds is not None:
            duration = _format_duration(duration_seconds)
        else:
            duration = None

        upload_date = data.get('upload_date')

        if not url:
            return None

        return YouTubeVideo(
            title=title,
            url=url,
            uploader=uploader,
            view_count=view_count,
            duration=duration,
            upload_date=upload_date,
        )
    except Exception:
        return None


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    if seconds >= 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def format_youtube_results(videos: list[YouTubeVideo], query: str) -> str:
    """Format YouTube search results for display.

    Args:
        videos: List of YouTubeVideo results
        query: The search query that produced these results

    Returns:
        Formatted string for display to user
    """
    if not videos:
        return (
            f"[YouTube Search: {query}]\n\n"
            f"No results found for '{query}'. "
            f"Try different keywords or check your internet connection."
        )

    lines = [f"[YouTube Search: **{query}**]", ""]
    lines.append(f"Found {len(videos)} video(s):")
    lines.append("")

    for i, video in enumerate(videos, 1):
        lines.append(f"{i}. {video.formatted()}")
        lines.append("")

    lines.append("To add a video to your knowledge base, say: 'add video [number]'")
    lines.append("To research more via web search, say: 'find me more like this on [topic]'")

    return "\n".join(lines)
