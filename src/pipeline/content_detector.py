import re
from urllib.parse import urlparse


def detect_content_type(input_str: str) -> str:
    stripped = input_str.strip()

    if stripped.startswith(("http://", "https://")):
        parsed = urlparse(stripped)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()

        if "youtube.com" in netloc or "youtu.be" in netloc:
            return "youtube"
        if path.endswith(".pdf") or netloc.endswith(".pdf"):
            return "pdf"
        return "article"

    if len(input_str) > 1000 and "\x00" in input_str:
        return "pdf"
    if "\n" in input_str and len(input_str) > 100:
        return "text"
    if len(input_str) < 500 and not input_str.startswith("http"):
        return "text"
    return "text"


def extract_video_id(youtube_url: str) -> str:
    parsed = urlparse(youtube_url)

    if "youtube.com" in parsed.netloc.lower():
        if parsed.query and "v=" in parsed.query:
            match = re.search(r"(?:[?&])?v=([a-zA-Z0-9_-]+)", parsed.query)
            if match:
                return match.group(1)

    if "youtu.be" in parsed.netloc.lower():
        video_id = parsed.path.split("/")[-1]
        if video_id:
            return video_id

    raise ValueError("Invalid YouTube URL")
