import os
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import questionary

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
CLAUDE_MD_PATH = Path("CLAUDE.md")


def consult_claude_md(section: str = "What Works") -> str | None:
    """Read a section from CLAUDE.md for pattern consultation.

    Args:
        section: Section name to extract (e.g., "What Works", "Query Formulation Tips")

    Returns:
        Section content as string, or None if section not found
    """
    if not CLAUDE_MD_PATH.exists():
        return None

    try:
        content = CLAUDE_MD_PATH.read_text(encoding="utf-8")
        # Find section heading
        pattern = rf"## {re.escape(section)}\n\n(.*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    except Exception:
        return None


def update_claude_md(entry: str) -> bool:
    """Append a session note entry to CLAUDE.md Session Notes section.

    Args:
        entry: The session note to append (will be formatted with date)

    Returns:
        True if updated successfully, False otherwise
    """
    if not CLAUDE_MD_PATH.exists():
        return False

    try:
        content = CLAUDE_MD_PATH.read_text(encoding="utf-8")
        date_str = datetime.now().strftime("%Y-%m-%d")
        formatted_entry = f"- *[{date_str}]* {entry}\n"

        # Find Session Notes section
        if "## Session Notes" in content:
            # Append to existing section
            new_content = content.replace(
                "## Session Notes\n\n<!-- Agent appends patterns here after each research session -->",
                f"## Session Notes\n\n<!-- Agent appends patterns here after each research session -->\n{formatted_entry}",
            )
        else:
            # Add section at end
            new_content = content + f"\n## Session Notes\n\n{formatted_entry}"

        CLAUDE_MD_PATH.write_text(new_content, encoding="utf-8")
        return True
    except Exception:
        return False


def format_session_history(sessions: list[dict]) -> str:
    """Format research session history for display.

    Args:
        sessions: List of session dicts from database

    Returns:
        Formatted string showing session history
    """
    if not sessions:
        return "[Research History]\n\nNo research sessions recorded yet."

    lines = ["[Research History]", ""]

    for session in sessions:
        timestamp = session.get("timestamp", "")
        query = session.get("query", "")
        results_count = session.get("results_count", 0)
        deliverable_types = session.get("deliverable_types", "")
        seed_title = session.get("seed_content_title", "")

        # Format date
        try:
            dt = datetime.fromisoformat(timestamp)
            date_str = dt.strftime("%b %d, %Y")
        except Exception:
            date_str = timestamp[:10]

        lines.append(f"**{date_str}** — {query}")
        if seed_title:
            lines.append(f"  Seed: {seed_title}")
        lines.append(f"  Results: {results_count}")
        if deliverable_types:
            lines.append(f"  Deliverables: {deliverable_types}")
        lines.append("")

    return "\n".join(lines)


def build_research_query(content_item: dict, answers: dict) -> str:
    """Build composite search query from stored content + targeting answers + CLAUDE.md patterns.

    Consults CLAUDE.md "What Works" section for query formulation tips before building.

    Args:
        content_item: Dict with 'title' and 'topics' keys
        answers: Dict with 'aspect' and 'specific' keys from targeting questions

    Returns:
        Composite query string combining content context + user's focus area
    """
    tips = consult_claude_md("What Works")
    tip_context = f" {tips}" if tips else ""

    topic = content_item.get('title', '')
    aspect = answers.get('aspect') or ''
    specific = answers.get('specific') or ''

    parts = [topic]
    if aspect:
        parts.append(aspect)
    if specific:
        parts.append(specific)

    query = ' '.join(parts)

    if tip_context and len(tip_context) < 200:
        query += tip_context

    return query


async def ask_research_targeting_questions(
    topic_name: str,
    existing_content: list[dict],
) -> dict | None:
    """Ask 1-2 targeting questions before research.

    Generalized from gap_handler.ask_targeting_questions().

    Args:
        topic_name: The topic being researched
        existing_content: List of content item dicts with 'title' and 'topics'

    Returns:
        Dict with {'aspect': str, 'specific': str} or None if user declined
    """
    # Extract aspect options from stored content
    aspect_options = []
    for item in existing_content[:5]:
        if item.get('title'):
            aspect_options.append(item['title'][:50])

    if not aspect_options:
        aspect_options = ["General overview", "Best practices", "Common mistakes", "Recent developments"]
    else:
        aspect_options.extend(["General overview", "Other"])

    # Question 1: What aspect are you most interested in?
    aspect = await questionary.select(
        f"\n[Research Targeting]\n\n"
        f"Before I research \"{topic_name}\", a couple quick questions:\n\n"
        f"1. What specific aspect of \"{topic_name}\" are you most interested in?",
        choices=aspect_options[:4],  # Limit to 4 options
    ).ask_async()

    if aspect == "Other":
        aspect = await questionary.text(
            "What specific aspect would you like to explore?"
        ).ask_async()

    # Question 2: Specific focus (optional)
    specific = await questionary.text(
        "\n2. Is there anything specific you've been wondering about?\n"
        "(Press Enter to skip)"
    ).ask_async()

    return {
        'aspect': aspect if aspect != "Other" else None,
        'specific': specific if specific else None,
    }


def format_cited_results(results: list[dict], query: str) -> str:
    """Format Tavily research results into cited output.

    Args:
        results: List of result dicts from Tavily (each with 'title', 'url', 'content', 'highlights')
        query: The original search query

    Returns:
        Formatted string with citations, source URLs, and relevance explanations
    """
    if not results:
        return "[Research Results]\n\nI couldn't find any relevant results for your query."

    output = ["[Research Results]", "", f"Query: {query}", "", "---"]

    for i, result in enumerate(results, 1):
        title = result.get('title', 'Untitled')
        url = result.get('url', '')
        content = result.get('content', '')
        highlights = result.get('highlights', [])

        output.append(f"**{i}. {title}**")
        output.append(f"Source: {url}")
        output.append(f"Relevance: Found {len(highlights) if highlights else 1} relevant section(s) in this source")

        if highlights and len(highlights) > 0:
            output.append(f"Key finding: {highlights[0][:300]}{'...' if len(highlights[0]) >= 300 else ''}")
        elif content:
            output.append(f"Summary: {content[:200]}{'...' if len(content) >= 200 else ''}")

        output.append("")

    return "\n".join(output)
