# Phase 2: Memory & Surfacing - Research

**Researched:** 2026-03-26
**Domain:** Preference tracking, rejection storage, content surfacing, proactive knowledge delivery
**Confidence:** MEDIUM-HIGH

## Summary

Phase 2 adds memory and surfacing capabilities to the Legion Research Agent: storing user preferences (after explicit confirmation), warning when rejected approaches are mentioned, and surfacing relevant stored knowledge during conversations. The existing Phase 1 stack (SQLite WAL, aiosqlite, questionary) is sufficient -- no new libraries needed. The key design decision from Phase 1 (explicit confirmation, not inference) constrains the approach: preferences are only stored after user confirms "Should I remember that you prefer X over Y?" The surfacing algorithm uses simple keyword matching for v1; embeddings are deferred to v2 per INTEL-01.

**Primary recommendation:** Add two new SQLite tables (`preferences`, `rejection_warnings`), use questionary for the confirmation loop, implement keyword-based surfacing with topic/title matching, and integrate rejection checks into the agent loop.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PREF-01 | After comparison, agent asks "Should I remember that you prefer X over Y?" before updating profile | Confirmation loop via questionary; write to preferences table only on user confirm |
| PREF-02 | Rejections stored with: topic, approach, reason, date, source content | rejection_warnings table schema; source_content_id FK to content |
| PREF-03 | Preference profile human-readable and rewriteable (not just append) | Markdown file `knowledge/preferences.md` synced with SQLite; user edits propagate back |
| PREF-04 | Rejected approach warning fires when user mentions or uses a rejected approach | Message hook in agent loop; check normalized approach text against stored rejections |
| SURFACE-01 | User can ask "what do I have on X?" and agent returns relevant content with sources | surfacing query function with topic/content title keyword matching |
| SURFACE-02 | Agent proactively surfaces relevant knowledge during conversations when context matches | Context matching in agent loop (triggered on each user input) |
| SURFACE-03 | Each surfacing includes source URL, date, and brief description | surfacing response format: title, source_url, processed_date, 1-2 sentence summary |

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiosqlite | 0.22.1 | Async SQLite operations | Already installed, WAL mode compatible |
| questionary | 2.1.1 | Interactive CLI prompts | Already installed, clean async API for yes/no menus |
| python-dotenv | 1.2.2 | Environment variable loading | Already installed |

### No New Libraries Required
Phase 2 uses only existing installed packages. No new dependencies needed.

**Installation:** None required.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Keyword surfacing (v1) | Embeddings (sqlite-vec) | Embeddings deferred to v2 per INTEL-01; keyword matching sufficient for v1 |
| In-memory rejection checking | Separate rejection cache table | Keep it simple; SQLite is fast enough for rejection lookups |
| questionary confirm | Custom yes/no input loop | questionary is cleaner and already installed |

## Architecture Patterns

### Recommended Project Structure
```
src/
├── agent/
│   ├── loop.py                    # Modified: check preferences on each iteration
│   └── handlers/
│       ├── preference_handler.py  # NEW: confirmation loop, preference/rejection writes
│       ├── surfacing_handler.py   # NEW: "what do I have on X?", proactive surfacing
│       └── warning_handler.py     # NEW: rejection warning detection and display
├── storage/
│   ├── database.py                # Modified: add preferences/rejection_warnings tables
│   └── preference_store.py        # NEW: read/write preferences.md
knowledge/
├── preferences.md                 # NEW: human-readable preference profile
├── {topic}/
│   └── {content_id}.md            # Existing content markdown
```

### Pattern 1: Preference Storage Schema

**What:** Two SQLite tables for preferences and rejections, with a human-readable markdown file synced to SQLite.

**When to use:** Always, for storing user preferences.

**Schema:**
```sql
-- Preferences table: stores both confirmed preferences and rejections
CREATE TABLE preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,                    -- Topic/area this applies to
    preference_type TEXT NOT NULL,           -- 'prefer' or 'reject'
    approach TEXT NOT NULL,                 -- The specific approach
    reason TEXT,                            -- Optional reason
    source_content_id INTEGER REFERENCES content(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL                -- ISO timestamp
);

CREATE INDEX idx_preferences_topic ON preferences(topic);
CREATE INDEX idx_preferences_type ON preferences(preference_type);
```

**Why this schema:** Single table for both preferences and rejections (distinguished by `preference_type`) is simpler than two separate tables and allows easy querying for "all preferences on topic X". Indexes on topic and type for fast lookups during surfacing and warning checks.

**Example:**
```python
# Insert a preference after user confirms
await db.execute("""
    INSERT INTO preferences (topic, preference_type, approach, reason, source_content_id, created_at)
    VALUES (?, 'prefer', ?, ?, ?, datetime('now'))
""", (topic, preferred_approach, reason, source_content_id))

# Query rejections on a topic (for surfacing warnings)
async def get_topic_rejections(db, topic: str) -> list[dict]:
    cursor = await db.execute("""
        SELECT approach, reason, source_content_id FROM preferences
        WHERE topic = ? AND preference_type = 'reject'
    """, (topic,))
    return await cursor.fetchall()
```

### Pattern 2: Confirmation Loop for Preference Storage

**What:** After a comparison (user picks X over Y), agent asks "Should I remember that you prefer X over Y?" via questionary, then writes to preferences table only on user confirmation.

**When to use:** When user makes a choice between approaches during conversation.

**Example:**
```python
async def offer_preference记忆(
    preferred: str,
    rejected: str,
    topic: str,
    db: Database,
    source_content_id: int
) -> bool:
    """Ask user if they want to remember this preference.

    Returns True if user confirmed, False otherwise.
    """
    response = await questionary.confirm(
        f"Should I remember that you prefer **{preferred}** over **{rejected}**?",
        default=False
    ).ask_async()

    if response:
        await db.execute("""
            INSERT INTO preferences (topic, preference_type, approach, source_content_id, created_at)
            VALUES (?, 'prefer', ?, ?, datetime('now'))
        """, (topic, preferred, source_content_id))
        await db.commit()
        return True
    return False
```

### Pattern 3: Rejection Storage with Full Context

**What:** Rejections are stored with topic, approach, reason, date, and source content reference.

**When to use:** When user explicitly rejects an approach or says "don't use X" or "I prefer not to do Y".

**Example:**
```python
async def store_rejection(
    topic: str,
    rejected_approach: str,
    reason: str | None,
    source_content_id: int,
    db: Database
) -> None:
    """Store a rejection with full context."""
    await db.execute("""
        INSERT INTO preferences (topic, preference_type, approach, reason, source_content_id, created_at)
        VALUES (?, 'reject', ?, ?, ?, datetime('now'))
    """, (topic, rejected_approach, reason, source_content_id))
    await db.commit()
```

### Pattern 4: Rejection Warning Detection

**What:** On each user message, check if any rejected approaches are mentioned. If so, surface a warning with the stored reason.

**When to use:** On every user input in the agent loop.

**Algorithm:**
```python
async def check_for_rejection_warnings(user_message: str, db: Database) -> list[str]:
    """Check if user message mentions any rejected approaches.

    Returns list of warning messages to display.
    """
    warnings = []
    # Get all rejections
    cursor = await db.execute("SELECT topic, approach, reason FROM preferences WHERE preference_type = 'reject'")
    rejections = await cursor.fetchall()

    user_lower = user_message.lower()
    for rejection in rejections:
        # Normalize approach text for matching
        approach_normalized = rejection['approach'].lower().strip()
        # Check if approach is mentioned in user message
        if approach_normalized in user_lower:
            warning = f"[Rejection Warning] You mentioned **{rejection['approach']}**"
            if rejection['reason']:
                warning += f"\n  Reason: {rejection['reason']}"
            warnings.append(warning)

    return warnings
```

**Key insight:** Simple substring matching is sufficient for v1. More sophisticated matching (word boundaries, synonyms) deferred to v2 if needed.

### Pattern 5: Content Surfacing via Keyword Matching

**What:** Given a query topic X, find relevant content items by matching topic slugs and titles.

**When to use:** When user asks "what do I have on X?" or when agent proactively surfaces knowledge.

**Algorithm (v1 -- no embeddings):**
```python
async def surface_content(query: str, db: Database, limit: int = 5) -> list[dict]:
    """Find content relevant to query via keyword matching.

    Returns list of {content, relevance_score, matched_on}.
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())

    # Get all content with their topics
    all_content = await db.get_all_content()

    scored = []
    for content in all_content:
        score = 0
        matched_on = []

        # Check topic matches
        content_topics = await db.get_content_topics(content.id)
        for topic_slug in content_topics:
            if any(word in topic_slug.lower() for word in query_words):
                score += 2
                matched_on.append(f"topic: {topic_slug}")

        # Check title matches
        title_words = set(content.title.lower().split())
        overlap = query_words & title_words
        if overlap:
            score += len(overlap)
            matched_on.append(f"title: {content.title[:50]}")

        if score > 0:
            scored.append({
                'content': content,
                'score': score,
                'matched_on': matched_on
            })

    # Sort by score descending
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:limit]
```

**Format for surfacing response (SURFACE-03):**
```python
def format_surfaced_item(content, matched_on) -> str:
    return (
        f"**{content.title}**\n"
        f"- Source: {content.source_url or content.source_type}\n"
        f"- Date: {content.processed_date[:10]}\n"
        f"- Matched on: {', '.join(matched_on)}\n"
        f"- Summary: {content.raw_content[:200]}..."
    )
```

### Pattern 6: Proactive Surfacing in Agent Loop

**What:** On each iteration, after processing user input but before waiting, check if any stored content is relevant to the current context.

**When to use:** On every iteration of the agent loop.

**Integration point:** Add to `agent/loop.py` after checking inbox but before `asyncio.sleep()`:
```python
async def run_agent(poll_interval: float = POLL_INTERVAL):
    # ... existing setup ...

    try:
        while state.running:
            try:
                item = state.inbox.get_nowait()
                if item is not None:
                    from src.agent.handlers import process_content
                    await process_content(item, sync_manager)
            except asyncio.QueueEmpty:
                pass

            # NEW: Check for proactive surfacing
            # (Would need access to last user message -- store in state)
            if hasattr(state, 'last_user_message'):
                warnings = await check_for_rejection_warnings(state.last_user_message, db)
                if warnings:
                    for w in warnings:
                        print(w)

                surfaced = await find_proactive_surfacing(state.last_user_message, db)
                if surfaced:
                    print("\n[Relevant knowledge found]")
                    for item in surfaced[:3]:
                        print(format_surfaced_item(item['content'], item['matched_on']))

            state.iteration += 1
            await asyncio.sleep(poll_interval)
```

### Pattern 7: Human-Readable Preference Profile

**What:** A markdown file `knowledge/preferences.md` that mirrors the SQLite preferences table. User can read and edit it directly.

**When to use:** For PREF-03 (human-readable and rewriteable).

**File format:**
```markdown
# Legion Preferences

## Preferences

### Topic: trading-bots
- **Approach:** mean-reversion
  - Preferred over: momentum
  - Reason: more stable returns for my risk tolerance
  - Stored: 2026-03-26
  - Source: content #42

### Topic: content-creation
- **Approach:** AI-assisted
  - Reason: faster iteration
  - Stored: 2026-03-25

## Rejections

### Topic: trading-bots
- **Rejected:** martingale
  - Reason: unlimited downside risk
  - Stored: 2026-03-26
  - Source: content #38
```

**Sync mechanism:** On preference write, update markdown. On markdown edit (detected via file mtime change), parse and update SQLite.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Preference storage | Custom JSON file | SQLite preferences table | ACID compliance, concurrent access, already installed |
| Embeddings/semantic search | Build custom vector DB | Keyword matching (v1), sqlite-vec (v2) | INTEL-01 defers embeddings to v2; keyword sufficient for v1 |
| CLI yes/no prompts | Custom input() loop | questionary.confirm() | Already installed, cleaner UX, handles edge cases |
| Preference profile sync | In-memory only | Markdown file synced with SQLite | PREF-03 requires human-readable and rewriteable |

**Key insight:** User explicitly chose explicit confirmation (not inference). Don't add inference logic in v1 -- that would violate the core design decision from Phase 1.

## Common Pitfalls

### Pitfall 1: Forgetting to Normalize Text Before Matching
**What goes wrong:** "Mean Reversion" in stored preference doesn't match "mean reversion" in user message.
**Why it happens:** Case sensitivity and whitespace differences.
**How to avoid:** Always normalize both stored approach and user message to lowercase, strip whitespace, before comparing.
**Warning signs:** Users report "the warning didn't fire" despite mentioning rejected approach.

### Pitfall 2: Over-Triggering Rejection Warnings
**What goes wrong:** Common words trigger warnings (e.g., "I want to LEARN more" triggers rejection of "learn").
**Why it happens:** Substring matching is too loose.
**How to avoid:** Use word-boundary matching (regex `\b{word}\b`) or require minimum word length (5+ chars).
**Warning signs:** Users get annoyed by frequent irrelevant warnings.

### Pitfall 3: Preference File Drift
**What goes wrong:** SQLite preferences and markdown preferences get out of sync.
**Why it happens:** Only one side is updated (e.g., code writes to SQLite but markdown not updated).
**How to avoid:** Always write to both in same transaction or operation. On startup, reconcile differences.
**Warning signs:** User edits to preferences.md not reflected in behavior.

### Pitfall 4: Surfacing Too Much Irrelevant Content
**What goes wrong:** "what do I have on trading?" returns 50 items with low relevance.
**Why it happens:** No relevance threshold or limit.
**How to avoid:** Always limit results (default 5) and only surface items with score > 0. Sort by score.
**Warning signs:** Users ignore surfaced content or find it not helpful.

## Code Examples

### Database Schema Migration (add to `_init_db`)
```python
# Source: Based on Phase 1 database.py patterns (verified)
await self._conn.execute("""
    CREATE TABLE IF NOT EXISTS preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        preference_type TEXT NOT NULL CHECK(preference_type IN ('prefer', 'reject')),
        approach TEXT NOT NULL,
        reason TEXT,
        source_content_id INTEGER REFERENCES content(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
""")

await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_preferences_topic ON preferences(topic)")
await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_preferences_type ON preferences(preference_type)")
```

### Confirmation Loop (questionary)
```python
# Source: questionary 2.1.1 API (verified via pip show)
import questionary

async def ask_preference_confirmation(preferred: str, rejected: str, topic: str) -> bool:
    return await questionary.confirm(
        f"Should I remember that you prefer **{preferred}** over **{rejected}**?",
        default=False
    ).ask_async()
```

### Surfacing Query (keyword matching)
```python
# Source: Based on Phase 1 content detection patterns
async def surface_content(query: str, db: Database, limit: int = 5) -> list[dict]:
    query_words = set(query.lower().split())
    all_content = await db.get_all_content()

    scored = []
    for content in all_content:
        score = 0
        matched_on = []

        content_topics = await db.get_content_topics(content.id)
        for topic_slug in content_topics:
            if any(word in topic_slug.lower() for word in query_words):
                score += 2
                matched_on.append(f"topic: {topic_slug}")

        title_words = set(content.title.lower().split())
        overlap = query_words & title_words
        if overlap:
            score += len(overlap)
            matched_on.append(f"title: {content.title[:50]}")

        if score > 0:
            scored.append({'content': content, 'score': score, 'matched_on': matched_on})

    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:limit]
```

### Rejection Warning Check
```python
# Source: Standard Python regex for word-boundary matching
import re

async def check_rejection_warnings(user_message: str, db: Database) -> list[str]:
    warnings = []
    cursor = await db.execute(
        "SELECT topic, approach, reason FROM preferences WHERE preference_type = 'reject'"
    )
    rejections = await cursor.fetchall()

    for rejection in rejections:
        # Use word-boundary matching to avoid over-triggering
        pattern = r'\b' + re.escape(rejection['approach'].lower()) + r'\b'
        if re.search(pattern, user_message.lower()):
            warning = f"[Rejection Warning] **{rejection['approach']}**"
            if rejection['reason']:
                warning += f"\n  Reason: {rejection['reason']}"
            warnings.append(warning)

    return warnings
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Append-only preference logs | Rewritable markdown + SQLite | Phase 2 PREF-03 | Users can edit preferences directly |
| Inference-based preference detection | Explicit confirmation only | Phase 1 decision | User has full control, no surprises |
| Reactive surfacing only | Proactive + reactive surfacing | Phase 2 SURFACE-02 | Agent anticipates needs |
| Keyword-only search | Keyword (v1) / Embeddings (v2) | v2 per INTEL-01 | v1 is simpler, v2 more powerful |

**Deferred to v2:**
- Embeddings via `sqlite-vec` for semantic surfacing (INTEL-01, INTEL-02, INTEL-03)
- Engagement-based gap detection (INTEL-04)
- These are explicitly out of scope for v1 per roadmap

## Open Questions

1. **Should the preference confirmation hook into the existing summary flow?**
   - What we know: Summary menu shows 4 options after content. A "comparison" could happen when user picks one approach over another in conversation.
   - What's unclear: At what exact point in conversation does "comparison" occur? Is it explicit (user says "I prefer X") or contextual (user picks one of two options)?
   - Recommendation: Build comparison detection as a separate handler that looks for preference signals in user messages. Integrate with agent loop, not summary flow.

2. **Should rejections also trigger a confirmation, or are they always explicit?**
   - What we know: PREF-01 says "after comparison" implying the preference case has confirmation. PREF-02 doesn't mention confirmation for rejections.
   - What's unclear: If user says "don't use X", should agent ask "Should I remember that you reject X?" or just store it?
   - Recommendation: Require explicit confirmation for both preferences and rejections to maintain symmetry and user control.

3. **How to handle topic extraction for preferences?**
   - What we know: Content has topics via content_topics junction. Preferences have a topic field.
   - What's unclear: Should preference topic come from the source content's topic, or should user specify it?
   - Recommendation: Default to source content's primary topic, allow user to override.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pytest.ini` or `pyproject.toml` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| PREF-01 | Confirmation prompt appears after comparison | unit | `pytest tests/test_preference_handler.py::test_confirmation_prompt -x` | no |
| PREF-01 | Preference written to DB only on confirm | integration | `pytest tests/test_preference_handler.py::test_preference_write_on_confirm -x` | no |
| PREF-02 | Rejection stored with topic, approach, reason, date, source | integration | `pytest tests/test_preference_handler.py::test_rejection_stored -x` | no |
| PREF-03 | preferences.md exists and is human-readable | unit | `pytest tests/test_preference_store.py::test_preferences_md_readable -x` | no |
| PREF-03 | preferences.md edits sync back to SQLite | integration | `pytest tests/test_preference_store.py::test_preferences_md_sync -x` | no |
| PREF-04 | Warning fires when rejected approach mentioned | unit | `pytest tests/test_warning_handler.py::test_warning_fires_on_mention -x` | no |
| PREF-04 | No warning for non-rejected approaches | unit | `pytest tests/test_warning_handler.py::test_no_warning_for_non_rejected -x` | no |
| SURFACE-01 | "what do I have on X?" returns relevant content | unit | `pytest tests/test_surfacing_handler.py::test_surface_content_query -x` | no |
| SURFACE-01 | Surfaced content includes URL, date, description | unit | `pytest tests/test_surfacing_handler.py::test_surface_format -x` | no |
| SURFACE-02 | Proactive surfacing fires on context match | integration | `pytest tests/test_surfacing_handler.py::test_proactive_surfacing -x` | no |
| SURFACE-02 | No surfacing when no context match | unit | `pytest tests/test_surfacing_handler.py::test_no_surfacing_no_match -x` | no |
| SURFACE-03 | Each item includes source URL | unit | `pytest tests/test_surfacing_handler.py::test_item_has_url -x` | no |
| SURFACE-03 | Each item includes date | unit | `pytest tests/test_surfacing_handler.py::test_item_has_date -x` | no |
| SURFACE-03 | Each item includes brief description | unit | `pytest tests/test_surfacing_handler.py::test_item_has_description -x` | no |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_preference_handler.py` -- covers PREF-01, PREF-02
- [ ] `tests/test_preference_store.py` -- covers PREF-03
- [ ] `tests/test_warning_handler.py` -- covers PREF-04
- [ ] `tests/test_surfacing_handler.py` -- covers SURFACE-01, SURFACE-02, SURFACE-03
- [ ] `src/agent/handlers/preference_handler.py` -- NEW file for confirmation loop
- [ ] `src/agent/handlers/warning_handler.py` -- NEW file for rejection warnings
- [ ] `src/agent/handlers/surfacing_handler.py` -- NEW file for content surfacing
- [ ] `src/storage/preference_store.py` -- NEW file for preferences.md sync
- [ ] `src/storage/database.py` -- add preferences table migration

*(All Wave 0 files are new -- Phase 2 adds net-new functionality)*

## Sources

### Primary (HIGH confidence)
- aiosqlite 0.22.1 -- https://pypi.org/project/aiosqlite/ -- Already installed, verified via pip
- questionary 2.1.1 -- https://pypi.org/project/questionary/ -- Already installed, verified via pip
- SQLite Python docs -- https://docs.python.org/3/library/sqlite3.html -- Schema design patterns
- Phase 1 existing code -- `src/storage/database.py`, `src/agent/handlers/summary_handler.py` -- Verified working patterns

### Secondary (MEDIUM confidence)
- INTEL-01 through INTEL-04 from REQUIREMENTS.md -- v2 features, deferred to v2

### Tertiary (LOW confidence - not verified)
- Rejection warning word-boundary regex -- standard Python regex, may need field testing
- Surfacing relevance scoring (2 for topic, 1 for title overlap) -- heuristic, may need tuning

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- only existing packages used, no new dependencies
- Architecture: MEDIUM-HIGH -- SQLite schema design is straightforward; surfacing algorithm is simple heuristic that may need tuning
- Pitfalls: MEDIUM -- text normalization and over-triggering are known issues with keyword matching; mitigation strategies documented
- Surfacing quality: MEDIUM -- keyword matching is sufficient for v1; embeddings deferred to v2

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (30 days -- stable domain, no fast-moving libraries)
