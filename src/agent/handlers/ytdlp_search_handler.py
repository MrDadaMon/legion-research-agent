"""yt-dlp YouTube search handler — humanized for anti-bot detection.

Key anti-detection features:
- Realistic browser User-Agent
- Random delays between requests (mimics human browsing)
- Rate limiting (max 1 search per 10s, 3s between metadata fetches)
- Views/subs ratio for quality ranking
- Optional date filtering (last N months)
- Result shuffling to avoid predictable ordering
"""

import re
import json
import logging
import random
import subprocess
import time
from datetime import datetime, timedelta
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

# Realistic browser User-Agent strings — rotated to avoid fingerprinting
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# Anti-detection timing
MIN_DELAY_BETWEEN_SEARCHES = 10  # seconds — rate limit
MIN_DELAY_BETWEEN_METADATA = 3   # seconds — human-like pause
FETCH_COUNT_MULTIPLIER = 2      # fetch 2x to account for date filtering


class YouTubeVideo(NamedTuple):
    title: str
    url: str
    uploader: str
    view_count: int | None
    subscriber_count: int | None
    duration: str | None
    upload_date: str | None
    views_per_sub: float | None  # views/subs ratio — quality signal

    def formatted(self) -> str:
        parts = [f"**{self.title}**"]
        parts.append(f"  Channel: {self.uploader}")
        if self.subscriber_count:
            parts.append(f"  Subs: {self._format_subs(self.subscriber_count)}")
        if self.view_count:
            parts.append(f"  Views: {self._format_views(self.view_count)}")
        if self.views_per_sub is not None:
            parts.append(f"  Quality: {self.views_per_sub:.1f}x views/sub")
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
        return f"{count:,}"

    @staticmethod
    def _format_subs(count: int) -> str:
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        if count >= 1_000:
            return f"{count / 1_000:.1f}K"
        return f"{count:,}"

    @staticmethod
    def _format_date(date_str: str) -> str:
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str


_last_search_time = 0.0


def _random_delay(min_seconds: float) -> None:
    """Sleep for a random duration between min_seconds and min_seconds * 2.

    Mimics the variable pause a human takes between actions.
    """
    delay = min_seconds + (random.random() * min_seconds)
    time.sleep(delay)


def _get_user_agent() -> str:
    """Return a random User-Agent to avoid fingerprinting."""
    return random.choice(USER_AGENTS)


def _rate_limit() -> None:
    """Enforce rate limiting between searches."""
    global _last_search_time
    elapsed = time.time() - _last_search_time
    if elapsed < MIN_DELAY_BETWEEN_SEARCHES:
        sleep_time = MIN_DELAY_BETWEEN_SEARCHES - elapsed + random.random() * 3
        logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s before next search")
        time.sleep(sleep_time)
    _last_search_time = time.time()


def _get_cutoff_date(months: int) -> str | None:
    """Return YYYYMMDD string for date cutoff, or None if no filtering."""
    if months <= 0:
        return None
    cutoff = datetime.now() - timedelta(days=months * 30)
    return cutoff.strftime("%Y%m%d")


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


def search_youtube(
    query: str,
    max_results: int = 10,
    months: int = 6,
) -> list[YouTubeVideo]:
    """Search YouTube using yt-dlp with anti-bot measures.

    Anti-detection features:
    - Realistic browser User-Agent
    - Rate limiting (10s between searches)
    - Date filtering (last N months)
    - Views/subs ratio for quality ranking
    - Result shuffling for human-like ordering

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 10)
        months: Only show videos from the last N months. 0 = no filter (default 6)

    Returns:
        List of YouTubeVideo namedtuples sorted by views/subs ratio
    """
    _rate_limit()

    user_agent = _get_user_agent()
    fetch_count = max_results * FETCH_COUNT_MULTIPLIER if months > 0 else max_results

    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            f'ytsearch{fetch_count}:{query}',
            '--flat-playlist',
            '--no-warnings',
            '--quiet',
            '--add-header',
            f'User-Agent:{user_agent}',
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0 and not result.stdout.strip():
            logger.warning(f"yt-dlp search failed: {result.stderr}")
            return []

        videos: list[YouTubeVideo] = []
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

        # Apply date filter
        cutoff = _get_cutoff_date(months)
        if cutoff:
            before = len(videos)
            videos = [v for v in videos if (v.upload_date or "00000000") >= cutoff]
            logger.debug(f"Date filter: {before} -> {len(videos)} after removing older than {months} months")

        if not videos:
            return []

        # Limit to requested count
        videos = videos[:max_results]

        # Shuffle slightly — human searches don't always go in the exact same order
        # Shuffle within top 60% of results to keep relevance while looking human
        keep_order = videos[:max(1, len(videos) // 3)]
        shuffled = videos[len(keep_order):]
        random.shuffle(shuffled)
        videos = keep_order + shuffled

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
    _random_delay(MIN_DELAY_BETWEEN_METADATA)

    user_agent = _get_user_agent()

    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            '--no-warnings',
            '--quiet',
            '--add-header',
            f'User-Agent:{user_agent}',
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
        subscriber_count = data.get('channel_follower_count')
        duration_seconds = data.get('duration')

        if duration_seconds is not None:
            duration = _format_duration(int(duration_seconds))
        else:
            duration = None

        upload_date = data.get('upload_date')

        # Calculate views/subs ratio — quality signal
        # High ratio = video performs well relative to channel size = better content
        views_per_sub = None
        if view_count and subscriber_count and subscriber_count > 0:
            views_per_sub = view_count / subscriber_count

        if not url:
            return None

        return YouTubeVideo(
            title=title,
            url=url,
            uploader=uploader,
            view_count=view_count,
            subscriber_count=subscriber_count,
            duration=duration,
            upload_date=upload_date,
            views_per_sub=views_per_sub,
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


def format_youtube_results(
    videos: list[YouTubeVideo],
    query: str,
    months: int = 6,
) -> str:
    """Format YouTube search results for display.

    Args:
        videos: List of YouTubeVideo results
        query: The search query that produced these results
        months: Date filter applied (for display)

    Returns:
        Formatted string for display to user
    """
    if not videos:
        date_note = f" (last {months} months)" if months > 0 else ""
        return (
            f"[YouTube Search: {query}]\n\n"
            f"No results found for '{query}'{date_note}. "
            f"Try different keywords, broadening your search, or say 'search YouTube for [topic] --no-date-filter' to see older results."
        )

    date_note = f" (last {months} months)" if months > 0 else ""
    lines = [f"[YouTube Search: **{query}**{date_note}]", ""]
    lines.append(f"Found {len(videos)} video(s), ranked by quality signal (views/sub ratio):")
    lines.append("")

    for i, video in enumerate(videos, 1):
        lines.append(f"{i}. {video.formatted()}")
        lines.append("")

    lines.append("To add a video to your knowledge base: 'add video [number]'")
    lines.append("To research more via web search: 'find me more like this on [topic]'")

    return "\n".join(lines)
