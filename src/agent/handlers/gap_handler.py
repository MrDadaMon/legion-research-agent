import re
import questionary
from datetime import datetime, timedelta
from typing import Optional

from src.storage.database import Database
from src.models.content import ContentItem
from src.agent.research_utils import ask_research_targeting_questions


# Constants from 03-RESEARCH.md
GAP_CONTENT_THRESHOLD = 3  # 3+ pieces of content
GAP_IDLE_HOURS = 24  # 24h+ idle time
GAP_COOLDOWN_DAYS = 7  # Don't suggest more than once per week

# Common subtopics for gap identification (trading-focused for now)
COMMON_TRADING_SUBTOPICS = [
    'risk management',
    'position sizing',
    'entry criteria',
    'exit strategy',
    'backtesting',
    'paper trading',
    'live results',
    'psychology',
    'market analysis',
    'technical indicators',
    'fundamental analysis',
    'portfolio diversification',
    'automated execution',
]


def should_suggest_gap(topic_metadata: dict | None) -> tuple[bool, str]:
    """Check if gap suggestion should trigger based on topic metadata.

    Returns (should_suggest, reason).
    should_suggest is True when:
      - topic has 3+ content pieces
      - 24h+ since last content
      - 7+ days since last gap suggestion (or never)
    """
    if topic_metadata is None:
        return False, "No metadata"

    content_count = topic_metadata.get('content_count', 0)
    last_date_str = topic_metadata.get('last_content_date')

    if content_count < GAP_CONTENT_THRESHOLD:
        return False, f"Only {content_count} content pieces (need {GAP_CONTENT_THRESHOLD})"

    if not last_date_str:
        return False, "No last content date"

    # Parse last content date
    last_date = datetime.fromisoformat(last_date_str)
    hours_since = (datetime.now() - last_date).total_seconds() / 3600

    if hours_since < GAP_IDLE_HOURS:
        return False, f"Only {hours_since:.1f} hours since last content (need {GAP_IDLE_HOURS}h)"

    # Check cooldown
    last_suggestion = topic_metadata.get('last_gap_suggestion')
    if last_suggestion:
        suggestion_date = datetime.fromisoformat(last_suggestion)
        days_since = (datetime.now() - suggestion_date).days
        if days_since < GAP_COOLDOWN_DAYS:
            return False, f"Gap suggested {days_since} days ago (cooldown: {GAP_COOLDOWN_DAYS} days)"

    return True, f"Topic has {content_count} content pieces, {hours_since:.0f}h idle, ready for gap exploration"


def identify_gaps_from_content(topic_slug: str, content_items: list[ContentItem]) -> list[str]:
    """Identify potential gaps based on existing content analysis.

    Looks for:
      1. Common subtopics NOT mentioned in existing content
      2. Question patterns in existing content that might indicate unexplored areas

    Returns list of potential gap topics.
    """
    # Combine all content text for analysis
    all_text = ' '.join([
        f"{c.title} {c.raw_content[:300]}"
        for c in content_items
    ]).lower()

    # Find common subtopics NOT in existing content
    missing_subtopics = []
    for subtopic in COMMON_TRADING_SUBTOPICS:
        if subtopic not in all_text:
            missing_subtopics.append(subtopic)

    # Look for question patterns that indicate areas needing exploration
    questions_in_content = re.findall(
        r'(what|how|why|when|where|which|should|can|could)\s+(.{0,50}\?)',
        all_text
    )

    # Extract question stems that might indicate unaddressed gaps
    question_stems = set()
    for match in questions_in_content:
        question_stems.add(match[1].strip() if len(match) > 1 else '')

    # Combine missing subtopics with question-derived gaps
    # Deduplicate and limit to top 5
    gaps = missing_subtopics[:5]

    return gaps


async def present_gap_suggestion(
    topic_name: str,
    content_count: int,
    hours_idle: float,
) -> str:
    """Present gap exploration suggestion to user.

    Returns user's choice: 'yes', 'not_now', or 'never'.
    """
    response = await questionary.select(
        f"[Gap Exploration Suggestion]\n\n"
        f"I notice you have {content_count} pieces of content on \"{topic_name}\" "
        f"with no new additions in {hours_idle:.0f} hours.\n\n"
        f"Would you like me to explore what aspects of \"{topic_name}\" you might be missing?",
        choices=[
            "Yes, explore gaps",
            "Not now",
            "Never ask about this topic",
        ],
    ).ask_async()

    if response.startswith("Yes"):
        return 'yes'
    elif response.startswith("Not"):
        return 'not_now'
    else:
        return 'never'


async def present_gap_results(
    topic_name: str,
    gaps: list[dict],
) -> list[str]:
    """Present gap research results with accept/reject per item.

    Each gap dict contains: {title, reason, search_query}

    Returns list of accepted gap titles (empty if none accepted).
    """
    if not gaps:
        print(f"\n[Gap Research Results for \"{topic_name}\"]")
        print("I couldn't find any obvious gaps to research. You might want to add more content first.")
        return []

    lines = [
        f"[Gap Research Results for \"{topic_name}\"]",
        "",
        f"I found {len(gaps)} potential gaps. For each, let me know if you want me to:",
        "  - Research this gap and add findings to your knowledge base",
        "  - Skip this one",
        "",
        "---",
        "",
    ]

    choices = []
    for i, gap in enumerate(gaps, 1):
        lines.append(f"{i}. {gap['title']}")
        lines.append(f"   Why this might be worth exploring: {gap['reason']}")
        lines.append(f"   Suggested search: \"{gap['search_query']}\"")
        lines.append("")
        choices.append(f"Research: {gap['title'][:40]}")
        choices.append(f"Skip: {gap['title'][:40]}")

    lines.extend(["---", "", "Bulk options:"])
    choices.append("Research all")
    choices.append("Skip all")

    # Present gaps one by one for accept/reject
    accepted = []

    for i, gap in enumerate(gaps, 1):
        response = await questionary.select(
            f"\n[Gap {i}/{len(gaps)}]: {gap['title']}\n"
            f"Why: {gap['reason']}\n"
            f"Search: \"{gap['search_query']}\"",
            choices=[
                "Research this",
                "Skip this",
            ],
        ).ask_async()

        if response.startswith("Research"):
            accepted.append(gap['title'])

    return accepted


async def store_gap_interest(
    topic_name: str,
    gap_title: str,
    search_query: str,
    db: Database,
) -> None:
    """Store user's interest in researching a gap.

    For v1: just log to console. In v2, could integrate with actual research pipeline.
    """
    print(f"\n[Gap Interest Stored]")
    print(f"Topic: {topic_name}")
    print(f"Gap: {gap_title}")
    print(f"Search query: {search_query}")
    print("Note: Actual gap research is a v2 feature.")


async def check_and_suggest_gap(
    topic_id: int,
    topic_name: str,
    topic_slug: str,
    db: Database,
) -> bool:
    """Main entry point: check if gap suggestion should trigger and present to user.

    Returns True if suggestion was presented (regardless of user choice).
    Returns False if conditions not met.
    """
    # Get topic metadata
    metadata = await db.get_topic_metadata(topic_id)

    # Check if should suggest
    should_suggest, reason = should_suggest_gap(metadata)

    if not should_suggest:
        return False

    # Get content for gap analysis
    content_items = await db.get_topic_content(topic_slug)

    # Calculate hours idle
    last_date = datetime.fromisoformat(metadata['last_content_date'])
    hours_idle = (datetime.now() - last_date).total_seconds() / 3600

    # Present suggestion
    choice = await present_gap_suggestion(
        topic_name=topic_name,
        content_count=metadata['content_count'],
        hours_idle=hours_idle,
    )

    if choice == 'never':
        # Update cooldown to far future (effectively permanent)
        # For v1, just skip - could add a topic setting later
        return True

    if choice == 'not_now':
        return True

    # User said yes - ask targeting questions
    answers = await ask_research_targeting_questions(topic_name, content_items)

    if answers is None:
        return True  # User declined

    # Generate gap research
    gaps = generate_gap_research(topic_name, answers)

    # Present results
    accepted = await present_gap_results(topic_name, gaps)

    # Store accepted gaps
    for gap in gaps:
        if gap['title'] in accepted:
            await store_gap_interest(
                topic_name=topic_name,
                gap_title=gap['title'],
                search_query=gap['search_query'],
                db=db,
            )

    return True


def generate_gap_research(topic_name: str, answers: dict) -> list[dict]:
    """Generate gap research based on user's answers.

    For v1: simple rule-based generation. In v2, could integrate with actual search.

    Returns list of gap dicts: {title, reason, search_query}
    """
    gaps = []
    aspect = answers.get('aspect') or topic_name
    specific = answers.get('specific')

    # Build gaps based on aspect
    if aspect and 'risk' in aspect.lower():
        gaps.extend([
            {
                'title': 'Position Sizing Strategies',
                'reason': 'Proper position sizing is crucial for risk management',
                'search_query': f'{aspect} position sizing strategies',
            },
            {
                'title': 'Risk/Reward Ratios',
                'reason': 'Understanding risk/reward helps validate trade entries',
                'search_query': f'{aspect} risk reward ratio analysis',
            },
        ])

    elif aspect and ('entry' in aspect.lower() or 'timing' in aspect.lower()):
        gaps.extend([
            {
                'title': 'Entry Timing Techniques',
                'reason': 'Better entry timing improves win rate',
                'search_query': f'{aspect} entry timing techniques',
            },
            {
                'title': 'Confirmation Indicators',
                'reason': 'Confirmation indicators validate entry signals',
                'search_query': f'{aspect} confirmation indicators',
            },
        ])

    elif aspect and ('exit' in aspect.lower() or 'strategy' in aspect.lower()):
        gaps.extend([
            {
                'title': 'Stop Loss Strategies',
                'reason': 'Proper stop loss placement is critical for capital preservation',
                'search_query': f'{aspect} stop loss strategies',
            },
            {
                'title': 'Take Profit Techniques',
                'reason': 'Know when to take profits vs let winners run',
                'search_query': f'{aspect} take profit techniques',
            },
        ])

    elif aspect and 'backtest' in aspect.lower():
        gaps.extend([
            {
                'title': 'Backtesting Best Practices',
                'reason': 'Proper backtesting methodology ensures reliable results',
                'search_query': f'{aspect} backtesting best practices',
            },
            {
                'title': 'Overfitting Prevention',
                'reason': 'Avoid curve fitting in your backtests',
                'search_query': f'{aspect} overfitting prevention',
            },
        ])

    else:
        # General gaps
        gaps.extend([
            {
                'title': 'Common Mistakes',
                'reason': 'Learn from others\' errors to avoid costly mistakes',
                'search_query': f'{aspect} common mistakes to avoid',
            },
            {
                'title': 'Best Practices',
                'reason': 'Follow established best practices for better results',
                'search_query': f'{aspect} best practices guide',
            },
            {
                'title': 'Psychology and Discipline',
                'reason': 'Trading psychology is often the difference between success and failure',
                'search_query': f'{aspect} trading psychology discipline',
            },
        ])

    # Add specific question gap if provided
    if specific:
        gaps.insert(0, {
            'title': f'Specific: {specific[:50]}',
            'reason': 'Based on your specific question',
            'search_query': specific,
        })

    return gaps[:5]  # Limit to 5 gaps
