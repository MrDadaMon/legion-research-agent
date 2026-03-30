from __future__ import annotations
import questionary

from src.storage.database import Database


async def offer_preference_memory(
    preferred: str,
    rejected: str,
    topic: str,
    db: Database,
    source_content_id: int | None = None,
    reason: str | None = None,
) -> bool:
    """Ask user if they want to remember a preference.

    After a comparison where user picks X over Y, call this to ask:
    'Should I remember that you prefer X over Y?'

    Returns True if user confirmed, False otherwise.
    If confirmed, stores the preference in the database.
    """
    response = await questionary.confirm(
        f"Should I remember that you prefer **{preferred}** over **{rejected}**?",
        default=False,
    ).ask_async()

    if response:
        await db.insert_preference(
            topic=topic,
            preference_type='prefer',
            approach=preferred,
            reason=reason,
            source_content_id=source_content_id,
        )
        await db.insert_preference(
            topic=topic,
            preference_type='reject',
            approach=rejected,
            reason=reason,
            source_content_id=source_content_id,
        )
        return True
    return False


async def store_rejection(
    topic: str,
    rejected_approach: str,
    db: Database,
    source_content_id: int | None = None,
    reason: str | None = None,
) -> bool:
    """Ask user if they want to remember a rejection.

    When user explicitly rejects an approach, call this to ask:
    'Should I remember that you reject X?'

    Returns True if user confirmed, False otherwise.
    """
    response = await questionary.confirm(
        f"Should I remember that you reject **{rejected_approach}**?",
        default=False,
    ).ask_async()

    if response:
        await db.insert_preference(
            topic=topic,
            preference_type='reject',
            approach=rejected_approach,
            reason=reason,
            source_content_id=source_content_id,
        )
        return True
    return False


def detect_comparison(user_message: str) -> dict | None:
    """Detect if user message contains a comparison (X vs Y, X over Y, etc).

    Returns dict with {preferred, rejected, topic} if comparison detected, None otherwise.
    This is a simple heuristic-based detector for v1.
    """
    import re

    comparison_patterns = [
        (r'prefer\s+([\w-]+)\s+over\s+([\w-]+)', 2),
        (r'([\w-]+)\s+over\s+([\w-]+)', 2),
        (r'rather\s+than\s+([\w-]+)', 1),
        (r'([\w-]+)\s+vs\.?\s+([\w-]+)', 2),
        (r'([\w-]+)\s+versus\s+([\w-]+)', 2),
    ]

    user_lower = user_message.lower()

    for pattern, num_groups in comparison_patterns:
        match = re.search(pattern, user_lower)
        if match:
            groups = match.groups()
            if num_groups == 2:
                return {
                    'preferred': groups[0].strip(),
                    'rejected': groups[1].strip(),
                    'topic': 'general',
                }
            elif num_groups == 1:
                return {
                    'preferred': 'this approach',
                    'rejected': groups[0].strip(),
                    'topic': 'general',
                }
    return None