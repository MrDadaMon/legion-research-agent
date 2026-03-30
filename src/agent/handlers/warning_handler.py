from __future__ import annotations
from src.storage.database import Database


async def check_for_rejection_warnings(
    user_message: str,
    db: Database,
) -> list[str]:
    """Check if user message mentions any rejected approaches.

    Returns list of warning messages to display to user.
    Each warning includes the rejected approach and stored reason (if any).
    Uses word-boundary matching to prevent over-triggering.
    """
    matches = await db.check_rejection_match(user_message)

    warnings = []
    for match in matches:
        warning = f"[Rejection Warning] You mentioned **{match['approach']}**"
        if match['reason']:
            warning += f"\n  Reason: {match['reason']}"
        if match['topic']:
            warning += f"\n  Topic: {match['topic']}"
        warnings.append(warning)

    return warnings


def format_warning_message(approach: str, reason: str | None, topic: str | None) -> str:
    """Format a single rejection warning message."""
    msg = f"[Rejection Warning] **{approach}**"
    if reason:
        msg += f"\n  Reason: {reason}"
    if topic:
        msg += f"\n  Topic: {topic}"
    return msg