import re

import questionary

from src.storage.database import Database


async def show_summary_menu(content_id: int, title: str) -> str:
    """Show 4-option quick-select menu after content processing.

    Returns: selected option string
    """
    choice = await questionary.select(
        f"Content processed: **{title}**\n\nWhat would you like to do?",
        choices=[
            "Quick Summary",
            "Full Breakdown",
            "Ask a Question",
            "Save for Later",
        ],
    ).ask_async()
    return choice


async def quick_summary(content_id: int, db: Database) -> str:
    """Return 3-5 key points as markdown bullets."""
    content = await db.get_content(content_id)
    if not content:
        raise ValueError(f"Content {content_id} not found")

    if len(content.raw_content) < 50:
        return f"- {content.raw_content.strip()}"

    sentences = re.split(r'(?<=[.!?])\s+|\n+', content.raw_content)
    meaningful = [
        s.strip() for s in sentences
        if len(s.strip()) >= 10
        and not any(skip in s.lower() for skip in [
            "subscribe", "copyright", "all rights reserved",
            "click here", "sign up", "newsletter", "follow me",
        ])
    ]

    bullets = meaningful[:5]
    if not bullets:
        bullets = [s.strip() for s in sentences if s.strip()][:5]

    return "\n".join(f"- {b}" for b in bullets)


async def full_breakdown(content_id: int, db: Database) -> str:
    """Return structured notes with key moments, quotes, and follow-up questions."""
    content = await db.get_content(content_id)
    if not content:
        raise ValueError(f"Content {content_id} not found")

    text = content.raw_content
    lines = []

    lines.append("## Key Moments")
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
    significant = [s.strip() for s in sentences if len(s.strip()) >= 15][:3]
    for i, sent in enumerate(significant):
        lines.append(f"- {sent}")
    if not significant:
        lines.append("- (No specific moments extracted)")

    lines.append("")
    lines.append("## Key Quotes")
    quote_pattern = re.compile(r'[""]([^""]+)[""]|([^.!?]*[.!?])')
    quotes = []
    for match in quote_pattern.finditer(text):
        quote = match.group(1) or match.group(2)
        if quote and len(quote.strip()) >= 10:
            quotes.append(quote.strip())
    for q in quotes[:3]:
        lines.append(f"> {q}")
    if not quotes:
        lines.append("> (No quotes found)")

    lines.append("")
    lines.append("## Follow-up Questions")
    keywords = re.findall(r'\b[a-zA-Z]{4,}\b', text)
    keyword_counts: dict[str, int] = {}
    for kw in keywords:
        k = kw.lower()
        keyword_counts[k] = keyword_counts.get(k, 0) + 1
    top_keywords = sorted(keyword_counts, key=keyword_counts.get, reverse=True)[:3]
    for kw in top_keywords:
        lines.append(f"- What more can you tell me about {kw}?")
    if not top_keywords:
        lines.append("- What are the main takeaways from this content?")
        lines.append("- What would you like to explore further?")

    return "\n".join(lines)


async def ask_question_mode(content_id: int, db: Database, question: str) -> str:
    """Search content for relevant sentences matching user question keywords."""
    content = await db.get_content(content_id)
    if not content:
        raise ValueError(f"Content {content_id} not found")

    keywords = re.findall(r'\b[a-zA-Z]{4,}\b', question)
    if not keywords:
        return "I couldn't find anything about that in the content. Could you rephrase or ask about something more specific?"

    text_lower = content.raw_content.lower()
    matches = []
    for kw in keywords:
        kw_lower = kw.lower()
        for sent in re.split(r'(?<=[.!?])\s+|\n+', content.raw_content):
            if kw_lower in sent.lower() and len(sent.strip()) >= 10:
                if sent not in matches:
                    matches.append(sent.strip())

    if matches:
        result_lines = ["Based on the content:"]
        for m in matches[:3]:
            result_lines.append(f"> {m}")
        result_lines.append("")
        return "\n".join(result_lines)

    return "I couldn't find anything about that in the content. Could you rephrase or ask about something more specific?"


async def save_for_later(content_id: int, db: Database) -> str:
    """Mark content as deferred for later retrieval."""
    content = await db.get_content(content_id)
    if not content:
        raise ValueError(f"Content {content_id} not found")

    return (
        f"**Saved for later:** {content.title}\n\n"
        "Use 'what do I have on X?' to retrieve this content anytime."
    )
