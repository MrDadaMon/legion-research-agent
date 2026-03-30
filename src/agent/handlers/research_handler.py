from __future__ import annotations
import os
import re
from dotenv import load_dotenv
from tavily import TavilyClient

from src.storage.database import Database
from src.agent.research_utils import (
    ask_research_targeting_questions,
    build_research_query,
    format_cited_results,
    consult_claude_md,
    update_claude_md,
    format_session_history,
)

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

RESEARCH_TRIGGER_PATTERNS = [
    r'find\s+me\s+more\s+like\s+this',
    r'search\s+for\s+more\s+on',
    r'research\s+more\s+on',
    r'look\s+up\s+more\s+about',
    r'get\s+more\s+info\s+on',
    r'find\s+more\s+about',
]

RESEARCH_HISTORY_PATTERNS = [
    r'what\s+have\s+i\s+researched',
    r"what's?\s+my\s+research\s+history",
    r'show\s+(?:me\s+)?my\s+research\s+history',
    r'research\s+history',
]


def is_research_query(user_message: str) -> bool:
    """Detect if user is requesting research on stored content.

    Examples: "find me more like this", "search for more on X",
              "research more on X", "look up more about X"
    """
    user_lower = user_message.lower().strip()
    for pattern in RESEARCH_TRIGGER_PATTERNS:
        if re.search(pattern, user_lower):
            return True
    return False


def is_research_history_query(user_message: str) -> bool:
    """Detect if user is asking for their research history.

    Examples: "what have I researched?", "show my research history"
    """
    user_lower = user_message.lower().strip()
    for pattern in RESEARCH_HISTORY_PATTERNS:
        if re.search(pattern, user_lower):
            return True
    return False


async def handle_research_history(db: Database, limit: int = 10) -> str:
    """Return formatted research session history."""
    sessions = await db.get_recent_sessions(limit=limit)
    return format_session_history(sessions)


def extract_content_reference(user_message: str) -> str | None:
    """Extract content/topic reference from research request.

    E.g., "find me more like this on trading bots" -> "trading bots"
    Returns None if no specific topic mentioned (use currently selected content).
    """
    match = re.search(
        r'find\s+me\s+more\s+like\s+this\s+on\s+(.+?)(?:\?|$)',
        user_message.lower()
    )
    if match:
        return match.group(1).strip()

    match = re.search(
        r'(?:search|research|look\s+up|get\s+more\s+info)\s+(?:for\s+more\s+on\s+|more\s+on\s+|up\s+more\s+about\s+|info\s+on\s+)(.+?)(?:\?|$)',
        user_message.lower()
    )
    if match:
        return match.group(1).strip()

    return None


def extract_content_for_research(
    user_message: str,
    all_content: list,
    default_content: dict | None = None,
) -> dict | None:
    """Determine which stored content to use as seed for research.

    If user specifies "on X", find content matching X.
    Otherwise use default_content (most recent or selected).
    """
    topic_ref = extract_content_reference(user_message)

    if topic_ref:
        # Find content matching the topic reference
        topic_lower = topic_ref.lower()
        for content in all_content:
            if topic_lower in content.get('title', '').lower():
                return content
        return None

    return default_content


async def execute_research(query: str, max_results: int = 5) -> list[dict]:
    """Execute web research using Tavily /research endpoint.

    Args:
        query: Composite search query
        max_results: Maximum number of results to return (default 5)

    Returns:
        List of result dicts with 'title', 'url', 'content', 'highlights'

    Raises:
        ValueError: If TAVILY_API_KEY is not set
    """
    api_key = TAVILY_API_KEY
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set in environment. Add it to your .env file.")

    client = TavilyClient(api_key=api_key)

    result = client.research(
        query=query,
        max_results=max_results,
        include_answer=True,
        include_highlights=True,
    )

    return result.get('results', [])


async def handle_research_request(
    user_message: str,
    db: Database,
    default_content_id: int | None = None,
) -> str:
    """Main entry point for research-on-demand requests.

    Flow:
    1. Detect if message is a research request
    2. Identify which stored content to use as seed
    3. Ask 1-2 targeting questions
    4. Build composite query from content + answers
    5. Execute Tavily research
    6. Format and return cited results

    Args:
        user_message: The user's message
        db: Database instance
        default_content_id: ID of currently selected content (or most recent)

    Returns:
        Formatted research results string
    """
    # Get all content for matching
    all_content = await db.get_all_content()

    # Convert ContentItem objects to dicts for research_utils
    content_dicts = [
        {
            'id': c.id,
            'title': c.title,
            'source_type': c.source_type,
            'source_url': c.source_url,
            'raw_content': c.raw_content[:500] if c.raw_content else '',
        }
        for c in all_content
    ]

    # Get default content
    default_content = None
    if default_content_id:
        default_content = await db.get_content(default_content_id)

    # Determine which content to use
    seed_content = extract_content_for_research(user_message, content_dicts, default_content)

    if not seed_content:
        return (
            "[Research Request]\n\n"
            "I couldn't find any stored content matching your request. "
            "Try saying 'find me more like this on [topic]' or add some content first."
        )

    topic_name = seed_content.get('title', 'Unknown Topic')

    # Ask targeting questions
    answers = await ask_research_targeting_questions(topic_name, content_dicts)

    if answers is None:
        return "[Research Request]\n\nResearch cancelled."

    # Build composite query
    query = build_research_query(seed_content, answers)

    # Insert research session log before executing
    session_id = await db.insert_research_session(
        query=query,
        seed_content_id=seed_content.get('id') if seed_content else None,
    )

    # Execute research
    try:
        results = await execute_research(query)
    except ValueError as e:
        await db.update_research_session(session_id, results_count=0, notes=str(e))
        return f"[Research Error]\n\n{str(e)}"
    except Exception as e:
        await db.update_research_session(session_id, results_count=0, notes=str(e))
        return f"[Research Error]\n\nFailed to execute research: {str(e)}"

    # Update session with results count
    await db.update_research_session(session_id, results_count=len(results))

    # Prompt for pattern notes to CLAUDE.md
    update_claude_md(
        f"Researched \"{topic_name}\" with query \"{query}\" — {len(results)} results. "
        f"Patterns noticed: [agent should observe what worked and append here]"
    )

    # Format results
    return format_cited_results(results, query)
