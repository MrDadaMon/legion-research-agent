import re
from src.storage.database import Database
from src.models.content import ContentItem


async def surface_content(
    query: str,
    db: Database,
    limit: int = 5,
) -> list[dict]:
    """Find content relevant to query via keyword matching.

    Returns list of dicts: {content, score, matched_on}
    - content: ContentItem
    - score: relevance score (higher = more relevant)
    - matched_on: list of strings like "topic: trading-bots" or "title: ..."

    Scoring:
    - Topic match: +2 per matching topic
    - Title word overlap: +1 per matching word
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())

    all_content = await db.get_all_content()

    scored = []
    for content in all_content:
        score = 0
        matched_on = []

        # Check topic matches (2 points each)
        content_topics = await db.get_content_topics(content.id)
        for topic_slug in content_topics:
            topic_words = set(topic_slug.lower().split('-'))
            overlap = query_words & topic_words
            if overlap:
                score += 2 * len(overlap)
                matched_on.append(f"topic: {topic_slug}")

        # Check title matches (1 point per word)
        title_words = set(content.title.lower().split())
        title_overlap = query_words & title_words
        if title_overlap:
            score += len(title_overlap)
            matched_on.append(f"title: {content.title[:50]}")

        if score > 0:
            scored.append({
                'content': content,
                'score': score,
                'matched_on': matched_on,
            })

    # Sort by score descending
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:limit]


def format_surfaced_item(content: ContentItem, matched_on: list[str]) -> str:
    """Format a surfaced content item for display.

    Includes source URL, date, and brief description per SURFACE-03.
    """
    # Get source string
    source = content.source_url if content.source_url else content.source_type

    # Truncate content for description (first 150 chars)
    description = content.raw_content[:150].strip()
    if len(content.raw_content) > 150:
        description += "..."

    # Format date
    date = content.processed_date[:10] if content.processed_date else "unknown"

    return (
        f"**{content.title}**\n"
        f"- Source: {source}\n"
        f"- Date: {date}\n"
        f"- Matched on: {', '.join(matched_on)}\n"
        f"- Summary: {description}"
    )


def is_surface_query(user_message: str) -> bool:
    """Detect if user message is asking about stored content.

    Examples: "what do I have on X?", "show me content about X",
              "what's my knowledge on X?", "do I have anything about X?"
    """
    surface_patterns = [
        r'what\s+do\s+i\s+have\s+on',
        r'what\s+do\s+i\s+know\s+about',
        r"what's?\s+my\s+knowledge\s+on",
        r'show\s+me\s+content\s+about',
        r'do\s+i\s+have\s+anything\s+about',
        r'what\s+have\s+i\s+stored\s+on',
        r"what's?\s+in\s+my\s+knowledge\s+on",
    ]

    user_lower = user_message.lower().strip()

    for pattern in surface_patterns:
        if re.search(pattern, user_lower):
            return True

    return False


def extract_surface_topic(user_message: str) -> str:
    """Extract the topic from a surface query.

    E.g., "what do I have on trading bots?" -> "trading bots"
    """
    # Remove common prefixes
    cleaned = user_message.lower()
    prefixes_to_remove = [
        r"what\s+do\s+i\s+have\s+on\s+",
        r"what\s+do\s+i\s+know\s+about\s+",
        r"what's?\s+my\s+knowledge\s+on\s+",
        r"what's?\s+in\s+my\s+knowledge\s+on\s+",
        r"show\s+me\s+content\s+about\s+",
        r"do\s+i\s+have\s+anything\s+about\s+",
        r"what\s+have\s+i\s+stored\s+on\s+",
    ]

    for prefix in prefixes_to_remove:
        cleaned = re.sub(prefix, '', cleaned)

    # Remove trailing punctuation
    cleaned = cleaned.strip('?.,!')

    return cleaned if cleaned else ""


async def find_proactive_surfacing(
    user_message: str,
    db: Database,
    threshold: int = 3,
    limit: int = 3,
) -> list[dict]:
    """Check if user message context matches any stored content.

    Returns up to limit items with score >= threshold.
    This is called proactively on each user message.

    Scoring: Same as surface_content (topic: 2pts, title: 1pt)
    """
    # Don't surface if user is explicitly asking
    if is_surface_query(user_message):
        return []

    return await surface_content(user_message, db, limit=limit)
