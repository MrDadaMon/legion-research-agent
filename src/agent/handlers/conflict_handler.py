import questionary
from src.storage.database import Database
from src.storage.embedding_store import EmbeddingStore, generate_content_embedding
from src.models.content import ContentItem


# Opposing keyword pairs for disagreement detection (from 03-RESEARCH.md)
OPPOSING_PAIRS = [
    ('not', 'do'),
    ('never', 'always'),
    ('avoid', 'use'),
    ('wrong', 'correct'),
    ('bad', 'good'),
    ('fail', 'succeed'),
    ('lose', 'win'),
    ('risk', 'safe'),
    ('lose', 'gain'),
]


def extract_key_points(content: str, num_points: int = 3) -> list[str]:
    """Extract key points from content (simple: first N sentences)."""
    sentences = content.replace('!', '.').replace('?', '.').split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences[:num_points]


def find_disagreements(summary_a: list[str], summary_b: list[str]) -> list[dict]:
    """Find disagreements between two summaries using opposing keyword pairs.

    Returns list of {source_a, source_b, type} for each disagreement found.
    """
    disagreements = []

    for a in summary_a:
        a_lower = a.lower()
        for b in summary_b:
            b_lower = b.lower()
            for pos, neg in OPPOSING_PAIRS:
                if pos in a_lower and neg in b_lower:
                    disagreements.append({
                        'source_a': a.strip(),
                        'source_b': b.strip(),
                        'type': f'"{pos}" vs "{neg}"'
                    })
                elif neg in a_lower and pos in b_lower:
                    disagreements.append({
                        'source_a': a.strip(),
                        'source_b': b.strip(),
                        'type': f'"{neg}" vs "{pos}"'
                    })

    return disagreements


async def check_for_conflicts(
    new_content_id: int,
    topic_slug: str,
    db: Database,
    embedding_store: EmbeddingStore,
) -> list[dict]:
    """Check if new content conflicts with existing content on same topic.

    Returns list of conflicts, each containing:
        - existing_content: ContentItem
        - new_content_id: int
        - disagreements: list of {source_a, source_b, type}
    Empty list means no conflict detected.
    """
    # Get the new content
    new_content = await db.get_content(new_content_id)
    if new_content is None:
        return []

    # Generate embedding for new content
    new_embedding = generate_content_embedding(new_content.title, new_content.raw_content)

    # Find similar content on same topic via embeddings
    similar = await embedding_store.find_similar_on_topic(
        topic_slug=topic_slug,
        embedding=new_embedding,
        exclude_content_id=new_content_id,
        limit=3
    )

    conflicts = []

    for sim in similar:
        # Get existing content
        existing_content = await db.get_content(sim['content_id'])
        if existing_content is None:
            continue

        # Extract key points from both
        new_points = extract_key_points(new_content.raw_content)
        existing_points = extract_key_points(existing_content.raw_content)

        # Check for disagreements
        disagreements = find_disagreements(new_points, existing_points)

        if disagreements:
            conflicts.append({
                'existing_content': existing_content,
                'new_content_id': new_content_id,
                'new_content': new_content,
                'disagreements': disagreements,
                'topic': topic_slug,
            })

    return conflicts


async def present_conflict(conflict: dict) -> str:
    """Present a conflict to the user and ask which approach they prefer.

    Returns the user's choice: 'existing', 'new', or 'both'.
    """
    existing = conflict['existing_content']
    new_content = conflict['new_content']

    lines = [
        "[Conflict Detected]",
        "",
        f"Topic: {conflict['topic']}",
        "",
        f"Source A: \"{existing.title}\"",
        "Key points:",
    ]

    for point in conflict['disagreements'][:3]:
        if point['source_a']:
            lines.append(f"  - {point['source_a'][:100]}")

    lines.extend([
        "",
        f"Source B: \"{new_content.title}\"",
        "Key points:",
    ])

    for point in conflict['disagreements'][:3]:
        if point['source_b']:
            lines.append(f"  - {point['source_b'][:100]}")

    lines.extend([
        "",
        "Key disagreement types found:",
    ])

    disagreement_types = set(d['type'] for d in conflict['disagreements'])
    for dtype in list(disagreement_types)[:5]:
        lines.append(f"  - {dtype}")

    lines.extend([
        "",
        "Which approach do you prefer?",
    ])

    choices = [
        f"Source A ({existing.title[:40]})",
        f"Source B ({new_content.title[:40]})",
        "Keep both (acknowledge conflict)",
    ]

    response = await questionary.select(
        "\n".join(lines),
        choices=choices,
    ).ask_async()

    if response.startswith("Source A"):
        return 'existing'
    elif response.startswith("Source B"):
        return 'new'
    else:
        return 'both'


async def resolve_conflict(
    conflict: dict,
    user_choice: str,
    db: Database,
) -> None:
    """Handle user's conflict resolution choice.

    Updates conflict_records and offers to store in preference profile.
    """
    from src.agent.handlers.preference_handler import offer_preference_memory

    existing = conflict['existing_content']
    new_content = conflict['new_content']

    # Summarize disagreements for record
    disagreement_summary = "; ".join([
        f"{d['type']}: {d['source_a'][:50]} vs {d['source_b'][:50]}"
        for d in conflict['disagreements'][:3]
    ])

    # Record in database
    conflict_id = await db.record_conflict(
        topic=conflict['topic'],
        content_a_id=existing.id,
        content_b_id=new_content.id,
        disagreement_summary=disagreement_summary,
        resolution=None  # Will update after user choice
    )

    if user_choice == 'existing':
        await db.resolve_conflict_record(conflict_id, 'a_preferred')
        # Offer to remember this preference
        await offer_preference_memory(
            preferred=existing.title,
            rejected=new_content.title,
            topic=conflict['topic'],
            db=db,
            source_content_id=new_content.id,
            reason=f"Conflict resolution: user preferred this over conflicting source",
        )

    elif user_choice == 'new':
        await db.resolve_conflict_record(conflict_id, 'b_preferred')
        await offer_preference_memory(
            preferred=new_content.title,
            rejected=existing.title,
            topic=conflict['topic'],
            db=db,
            source_content_id=new_content.id,
            reason=f"Conflict resolution: user preferred this over conflicting source",
        )

    else:  # 'both'
        await db.resolve_conflict_record(conflict_id, 'both_kept')


async def check_and_present_conflicts(
    new_content_id: int,
    topic_slug: str,
    db: Database,
    embedding_store: EmbeddingStore,
) -> bool:
    """Main entry point: check for conflicts and present to user if found.

    Returns True if conflicts were found and presented (regardless of resolution).
    Returns False if no conflicts detected.
    """
    conflicts = await check_for_conflicts(
        new_content_id=new_content_id,
        topic_slug=topic_slug,
        db=db,
        embedding_store=embedding_store,
    )

    if not conflicts:
        return False

    for conflict in conflicts:
        user_choice = await present_conflict(conflict)
        await resolve_conflict(conflict, user_choice, db)

    return True