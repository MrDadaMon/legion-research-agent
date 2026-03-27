# Phase 3: Intelligence Layer - Research

**Researched:** 2026-03-26
**Domain:** Conflict detection and resolution, gap detection and research, knowledge base intelligence
**Confidence:** MEDIUM-HIGH

## Summary

Phase 3 adds intelligence to the Legion Research Agent: detecting when new content conflicts with existing knowledge, presenting disagreements for user resolution, and identifying gaps in the user's knowledge base for potential research. The key technical decisions are: (1) use sentence-transformers (`all-MiniLM-L6-v2`) for embeddings stored via sqlite-vec, (2) detect conflicts via cosine similarity threshold of 0.85 on embeddings plus keyword overlap, (3) track idle time per topic to trigger gap suggestions after 3+ content pieces with 24h+ inactivity, (4) use the existing confirmation loop pattern from Phase 2 for conflict resolution. No new core libraries needed beyond sqlite-vec and sentence-transformers.

**Primary recommendation:** Build two new handlers (`conflict_handler.py`, `gap_handler.py`), add a `topic_metadata` table for idle time tracking, integrate sqlite-vec for embedding storage and similarity queries, and use the existing preference confirmation loop for conflict resolution.

## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for Phase 3. All design decisions are in my discretion.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONFLICT-01 | When new content overlaps with existing content on same topic, agent flags potential conflict | Embedding similarity (cosine 0.85) + topic match triggers conflict flag |
| CONFLICT-02 | Agent presents key points of disagreement between conflicting sources | Summary extraction + side-by-side presentation format |
| CONFLICT-03 | User resolves conflict by choosing preferred approach, updating preference profile | Uses existing offer_preference_memory pattern from Phase 2 |
| GAP-01 | After 3+ pieces of content on same topic with 24h+ idle, agent suggests gap exploration | topic_metadata table with last_content_date, checked on new intake |
| GAP-02 | Agent asks targeting questions before initiating gap research | 1-2 question prompt via questionary before research action |
| GAP-03 | Gap research results presented for user to decide whether to incorporate | Accept/reject format per item via questionary.select |

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiosqlite | 0.22.1 | Async SQLite operations | Already installed, WAL mode, compatible with vec0 extension |
| questionary | 2.1.1 | Interactive CLI prompts | Already installed, clean async API for confirm/select |

### New Dependencies Required
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite-vec | 0.1.7 | Vector similarity search in SQLite | Per INTEL-02, stores embeddings for semantic search |
| sentence-transformers | latest | Generate text embeddings | Per INTEL-01, `all-MiniLM-L6-v2` model for CPU-friendly embeddings |
| numpy | 2.4.3 | Array operations for embedding serialization | Required by sqlite-vec and sentence-transformers |

**Installation:**
```bash
pip install sqlite-vec sentence-transformers
```

**Version verification:**
```bash
pip show sqlite-vec       # 0.1.7 (verified 2026-03-26)
pip show sentence-transformers  # check latest
pip show numpy            # 2.4.3
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sqlite-vec | ChromaDB, Pinecone, FAISS | External DB adds complexity; sqlite-vec keeps everything in SQLite |
| all-MiniLM-L6-v2 | OpenAI embeddings (ada-002) | Local model is free, no API calls, privacy-friendly; ada-002 is better quality but costs money |
| Cosine similarity | L2/Euclidean distance | Cosine is better for normalized text embeddings; INTEL-03 specifies cosine threshold |

## Architecture Patterns

### Recommended Project Structure
```
src/
├── agent/
│   └── handlers/
│       ├── conflict_handler.py    # NEW: conflict detection, disagreement presentation
│       └── gap_handler.py         # NEW: gap detection, targeting questions, research
├── storage/
│   ├── database.py                # Modified: add topic_metadata table, conflict_records
│   └── embedding_store.py         # NEW: sqlite-vec wrapper for embeddings
knowledge/
├── preferences.md                 # Existing
├── {topic}/
│   └── {content_id}.md           # Existing content markdown
```

### Pattern 1: Embedding Storage with sqlite-vec

**What:** Store text embeddings in SQLite via sqlite-vec extension for fast cosine similarity queries.

**When to use:** For conflict detection (INTEL-03) and hybrid surfacing (INTEL-01).

**Schema:**
```python
# Load sqlite-vec extension
import sqlite3
import sqlite_vec

db = sqlite3.connect("knowledge/legion.db")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

# Create virtual table for content embeddings
# Note: Need to determine embedding dimension (384 for all-MiniLM-L6-v2)
```

**For aiosqlite integration (async):**
```python
import sqlite_vec
import aiosqlite

async def get_db_with_vec(db_path: str):
    db = await aiosqlite.connect(db_path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    return db
```

**Insert embedding for content:**
```python
from sentence_transformers import SentenceTransformer
from sqlite_vec import serialize_float32

model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embedding for content title + summary
text = f"{content.title}. {content.raw_content[:500]}"
embedding = model.encode(text)

# Store in sqlite-vec virtual table
await db.execute(
    "INSERT INTO content_embeddings(content_id, embedding) VALUES (?, ?)",
    [content.id, serialize_float32(embedding)]
)
```

**Query for similar content (conflict detection):**
```python
# Find content similar to new content on same topic (cosine similarity)
similar = await db.execute("""
    SELECT c.id, c.title, ce.content_id as similar_id,
           vec_distance_cosine(ce.embedding, ??) as distance
    FROM content_embeddings ce
    JOIN content c ON c.id = ce.content_id
    JOIN content_topics ct ON ct.content_id = c.id
    JOIN topics t ON t.id = ct.topic_id
    WHERE t.slug = ?
      AND c.id != ?
      AND vec_distance_cosine(ce.embedding, ??) < 0.15  # 1 - 0.85 = 0.15
    ORDER BY distance
    LIMIT 5
""", [new_embedding, topic_slug, new_content_id, new_embedding])
```

**Key insight:** sqlite-vec stores vectors as BLOB using `serialize_float32()`. Distance function `vec_distance_cosine` returns cosine distance (lower = more similar), so threshold 0.15 corresponds to cosine similarity of 0.85 (per INTEL-03).

### Pattern 2: Conflict Detection on Content Intake

**What:** When new content is processed, check for conflicts with existing content on same topic.

**When to use:** After content is extracted and stored, before presenting summary options.

**Algorithm:**
```python
async def check_for_conflicts(
    new_content_id: int,
    topic_slug: str,
    db: Database,
    embedding: list[float],
    similarity_threshold: float = 0.85,
) -> list[dict]:
    """Detect conflicts between new content and existing content on same topic.

    Returns list of conflicting content with disagreement details.
    """
    # 1. Find similar content on same topic via embeddings
    similar_content = await db.execute("""
        SELECT c.id, c.title, c.raw_content
        FROM content_embeddings ce
        JOIN content c ON c.id = ce.content_id
        JOIN content_topics ct ON ct.content_id = c.id
        JOIN topics t ON t.id = ct.topic_id
        WHERE t.slug = ?
          AND c.id != ?
          AND vec_distance_cosine(ce.embedding, ?) < ?
        ORDER BY vec_distance_cosine(ce.embedding, ?)
        LIMIT 3
    """, [topic_slug, new_content_id, embedding, 1 - similarity_threshold, embedding])

    conflicts = []
    for existing in similar_content:
        # 2. Extract key points from both (simple: first 3 sentences of summary)
        new_summary = extract_summary_key_points(new_content.raw_content)
        existing_summary = extract_summary_key_points(existing.raw_content)

        # 3. Check for disagreement (simple: keyword/topic overlap with opposite claims)
        disagreements = find_disagreements(new_summary, existing_summary)

        if disagreements:
            conflicts.append({
                'existing_content': existing,
                'new_content_id': new_content_id,
                'disagreements': disagreements,
            })

    return conflicts


def extract_summary_key_points(content: str, num_points: int = 3) -> list[str]:
    """Extract key points from content (simple: first N sentences)."""
    sentences = content.split('.')
    return [s.strip() for s in sentences[:num_points] if s.strip()]


def find_disagreements(summary_a: list[str], summary_b: list[str]) -> list[dict]:
    """Find disagreements between two summaries.

    For v1: simple keyword-based disagreement detection.
    Looks for opposing keywords (not vs do, always vs never, etc).
    """
    opposing_pairs = [
        ('not', 'do'), ('never', 'always'), ('avoid', 'use'),
        ('wrong', 'correct'), ('bad', 'good'), ('fail', 'succeed'),
    ]

    disagreements = []
    for a in summary_a:
        a_lower = a.lower()
        for b in summary_b:
            b_lower = b.lower()
            for pos, neg in opposing_pairs:
                if pos in a_lower and neg in b_lower:
                    disagreements.append({
                        'source_a': a,
                        'source_b': b,
                        'type': f'{pos} vs {neg}',
                    })
                elif neg in a_lower and pos in b_lower:
                    disagreements.append({
                        'source_a': a,
                        'source_b': b,
                        'type': f'{neg} vs {pos}',
                    })
    return disagreements
```

### Pattern 3: Conflict Presentation for User Resolution

**What:** Present conflicts in a clear format that lets user pick preferred approach.

**When to use:** When conflict is detected, before storing content.

**Presentation format:**
```
[Conflict Detected]

Topic: {topic_name}

Source A: "{existing_title}"
Key points:
  - {point 1}
  - {point 2}

Source B: "{new_title}"
Key points:
  - {point 1}
  - {point 2}

Key disagreement: {disagreement_type}

Which approach do you prefer?
  - Source A ({existing_title})
  - Source B ({new_title})
  - Keep both (acknowledge conflict)
```

**Integration with preference system:**
```python
async def resolve_conflict(
    conflict: dict,
    user_choice: str,  # 'existing', 'new', or 'both'
    db: Database,
):
    """Handle user's conflict resolution choice."""
    if user_choice == 'existing':
        # Store preference: prefer existing approach
        await offer_preference_memory(
            preferred=conflict['existing_content']['title'],
            rejected=conflict['new_title'],
            topic=conflict['topic'],
            db=db,
        )
    elif user_choice == 'new':
        # Store preference: prefer new approach
        await offer_preference_memory(
            preferred=conflict['new_title'],
            rejected=conflict['existing_content']['title'],
            topic=conflict['topic'],
            db=db,
        )
    # If 'both', just acknowledge and store without preference
```

### Pattern 4: Topic Idle Time Tracking (Gap Detection Trigger)

**What:** Track when topics have new content and trigger gap suggestions after inactivity.

**When to use:** On new content intake, check if topic should trigger gap suggestion.

**Database schema:**
```sql
CREATE TABLE IF NOT EXISTS topic_metadata (
    topic_id INTEGER PRIMARY KEY REFERENCES topics(id) ON DELETE CASCADE,
    last_content_date TEXT NOT NULL,           -- ISO timestamp of last content
    content_count INTEGER NOT NULL DEFAULT 0,   -- Number of content pieces
    last_gap_suggestion TEXT                    -- ISO timestamp of last gap suggestion
);
```

**Update on new content:**
```python
async def update_topic_on_new_content(topic_id: int, db: Database) -> bool:
    """Update topic metadata when new content is added.

    Returns True if gap suggestion should be triggered.
    """
    now = datetime.now().isoformat()

    # Get or create metadata
    cursor = await db.execute(
        "SELECT content_count, last_content_date FROM topic_metadata WHERE topic_id = ?",
        (topic_id,)
    )
    row = await cursor.fetchone()

    if row is None:
        # First content for this topic
        await db.execute(
            "INSERT INTO topic_metadata (topic_id, last_content_date, content_count) VALUES (?, ?, 1)",
            (topic_id, now)
        )
        return False

    content_count = row['content_count']
    last_date = datetime.fromisoformat(row['last_content_date'])
    hours_since = (datetime.now() - last_date).total_seconds() / 3600

    # Check if should suggest gap
    should_suggest = (
        content_count >= 3 and  # 3+ pieces
        hours_since >= 24 and    # 24h+ idle
        (row['last_gap_suggestion'] is None or
         (datetime.now() - datetime.fromisoformat(row['last_gap_suggestion'])).days >= 7)
        # Don't suggest more than once per week
    )

    # Update metadata
    await db.execute("""
        UPDATE topic_metadata
        SET last_content_date = ?, content_count = content_count + 1
        WHERE topic_id = ?
    """, (now, topic_id))

    return should_suggest
```

### Pattern 5: Gap Suggestion with Targeting Questions

**What:** Ask user 1-2 targeting questions before researching gaps.

**When to use:** When gap suggestion is triggered (3+ content, 24h+ idle).

**Question flow:**
```
[Gap Exploration Suggestion]

I notice you have {N} pieces of content on "{topic}" with no new additions in {X} days.

Would you like me to explore what aspects of "{topic}" you might be missing?

> Yes, explore gaps
> Not now
> Never ask about this topic

-- If user selects Yes --

Before I research, a few quick questions:

1. What aspect of "{topic}" are you most interested in?
   - [List 2-3 subtopics extracted from existing content]
   - Other: ____________

2. Is there anything specific you've been wondering about?
   - [Free text input]
```

**Gap identification (simple v1 approach):**
```python
def identify_gaps(topic_slug: str, existing_content: list[ContentItem]) -> list[str]:
    """Identify potential gaps based on existing content analysis.

    For v1: look for subtopics mentioned in other topics but not this one,
    or common subtopics that have shallow coverage.
    """
    # Extract common subtopics from content titles/summaries
    all_text = ' '.join([c.title + ' ' + c.raw_content[:200] for c in existing_content])

    # Look for question patterns (what, how, why, when, where)
    questions = re.findall(r'(what|how|why|when|where|which).{0,30}\?', all_text.lower())

    # Common trading/content/gap topics that might not be covered
    common_subtopics = [
        'risk management', 'position sizing', 'entry criteria', 'exit strategy',
        'backtesting', 'paper trading', 'live results', 'psychology',
    ]

    # Check which are NOT in existing content
    gaps = []
    for subtopic in common_subtopics:
        if subtopic not in all_text.lower():
            gaps.append(subtopic)

    return gaps[:5]  # Return top 5 potential gaps
```

### Pattern 6: Gap Research Results Presentation (Accept/Reject)

**What:** Present gap research results with clear accept/reject per item.

**When to use:** After gap research is complete.

**Presentation format:**
```
[Gap Research Results for "{topic}"]

I found {N} potential gaps. For each, let me know if you want me to:
  - Research this gap and add findings to your knowledge base
  - Skip this one

---

1. [Gap Title]
   - Why this might be worth exploring: {reason}
   - Suggested search: "{search_query}"

   > Research this
   > Skip

---

2. [Gap Title]
   ...

---

> Research all
> Skip all
```

**Storing accepted gaps:**
```python
async def store_gap_interest(
    topic: str,
    gap_description: str,
    search_query: str,
    db: Database,
) -> None:
    """Store user's interest in researching a gap.

    This could be a special type of preference or a separate gap_interests table.
    """
    await db.execute("""
        INSERT INTO gap_interests (topic, gap_description, search_query, created_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (topic, gap_description, search_query))
```

**Database schema for gap interests:**
```sql
CREATE TABLE IF NOT EXISTS gap_interests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    gap_description TEXT NOT NULL,
    search_query TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'researched', 'rejected'
    created_at TEXT NOT NULL
);
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Build custom ANN index or use external vector DB | sqlite-vec | Keeps everything in SQLite, no external dependencies, per INTEL-02 |
| Text embeddings | Use OpenAI API (costs money, adds latency) | sentence-transformers local model | Free, runs locally, privacy-friendly, good quality |
| Disagreement detection | Train ML model for contradiction detection | Simple keyword-based opposing pairs | Sufficient for v1, no training data needed |
| Gap identification | Complex topic modeling | Simple subtopic extraction from content keywords | Heuristic works for v1 |

**Key insight:** Phase 1 chose simplicity (keyword surfacing). Phase 3 should follow same philosophy: embeddings add real value for similarity, but complex ML (contradiction detection, topic modeling) is deferred to v2.

## Common Pitfalls

### Pitfall 1: Embedding Dimension Mismatch
**What goes wrong:** sqlite-vec throws error on query due to wrong dimension.
**Why it happens:** Model produces 384-dim vectors but virtual table created with wrong dimension.
**How to avoid:** Always create virtual table with exact dimension from model (384 for all-MiniLM-L6-v2). Store dimension in code as constant.

### Pitfall 2: Cosine Distance vs Similarity Confusion
**What goes wrong:** Using wrong threshold interpretation.
**Why it happens:** sqlite-vec's `vec_distance_cosine` returns DISTANCE (lower = more similar). INTEL-03 says "cosine similarity threshold 0.85" which means distance < 0.15.
**How to avoid:** Be explicit in code comments: `SIMILARITY_THRESHOLD = 0.85; DISTANCE_THRESHOLD = 1 - SIMILARITY_THRESHOLD`.

### Pitfall 3: Over-triggering Gap Suggestions
**What goes wrong:** Gap suggestion fires too often, annoying the user.
**Why it happens:** No cooldown period after suggestion.
**How to avoid:** Per GAP-01 pattern: track `last_gap_suggestion` per topic. Don't suggest more than once per week per topic.

### Pitfall 4: Confusing Conflict with Simple Disagreement
**What goes wrong:** Flagging content as conflicting when it's just different perspectives.
**Why it happens:** Overly sensitive disagreement detection.
**How to avoid:** Only flag as conflict when: (1) same topic AND (2) similar embedding (0.85+) AND (3) opposing key points. Require all three.

### Pitfall 5: sqlite-vec Extension Not Loading
**What goes wrong:** "no such module: vec0" error.
**Why it happens:** Extension not properly loaded with `enable_load_extension`.
**How to avoid:** Always call `db.enable_load_extension(True)` BEFORE `sqlite_vec.load(db)`, and `db.enable_load_extension(False)` after.

## Code Examples

### sqlite-vec Extension Loading with aiosqlite
```python
# Source: alexgarcia.xyz/sqlite-vec/python.html
import sqlite_vec
import aiosqlite

async def connect_db_with_vec(db_path: str):
    db = await aiosqlite.connect(db_path)
    await db.execute("PRAGMA enable_load_extension")
    sqlite_vec.load(db)
    await db.execute("PRAGMA disable_load_extension")
    return db
```

### Sentence Transformer Embedding Generation
```python
# Source: huggingface.co/sentence-transformers
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
# 384-dimensional embeddings, CPU-friendly, 22M params

def generate_content_embedding(title: str, content: str) -> list[float]:
    text = f"{title}. {content[:500]}"  # Truncate for speed
    embedding = model.encode(text)
    return embedding.tolist()
```

### Embedding Serialization for sqlite-vec
```python
# Source: alexgarcia.xyz/sqlite-vec/python.html
from sqlite_vec import serialize_float32
import numpy as np

# From list
embedding_list = [0.1, 0.2, 0.3]
serialized = serialize_float32(embedding_list)

# From numpy
embedding_np = np.array([0.1, 0.2, 0.3], dtype=np.float32)
await db.execute("INSERT INTO vec(content) VALUES (?)", [embedding_np])
```

### Conflict Detection Query
```python
SIMILARITY_THRESHOLD = 0.85
DISTANCE_THRESHOLD = 1 - SIMILARITY_THRESHOLD  # 0.15

async def find_similar_content(
    db,
    content_id: int,
    topic_slug: str,
    embedding,
    limit: int = 5
):
    """Find content similar to given content on same topic."""
    cursor = await db.execute("""
        SELECT c.id, c.title, c.raw_content,
               vec_distance_cosine(ce.embedding, ?) as distance
        FROM content_embeddings ce
        JOIN content c ON c.id = ce.content_id
        JOIN content_topics ct ON ct.content_id = c.id
        JOIN topics t ON t.id = ct.topic_id
        WHERE t.slug = ?
          AND c.id != ?
          AND distance < ?
        ORDER BY distance
        LIMIT ?
    """, [embedding, topic_slug, content_id, DISTANCE_THRESHOLD, limit])
    return await cursor.fetchall()
```

### Gap Suggestion Trigger Check
```python
async def should_suggest_gap(topic_id: int, db) -> bool:
    """Check if gap suggestion should trigger for a topic."""
    cursor = await db.execute("""
        SELECT content_count, last_content_date, last_gap_suggestion
        FROM topic_metadata
        WHERE topic_id = ?
    """, (topic_id,))
    row = await cursor.fetchone()

    if not row or row['content_count'] < 3:
        return False

    last_date = datetime.fromisoformat(row['last_content_date'])
    hours_since = (datetime.now() - last_date).total_seconds() / 3600

    if hours_since < 24:
        return False

    # Check cooldown
    if row['last_gap_suggestion']:
        days_since_suggestion = (datetime.now() - datetime.fromisoformat(row['last_gap_suggestion'])).days
        if days_since_suggestion < 7:
            return False

    return True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Keyword-only conflict detection (v1 start) | Embedding-based similarity + keyword overlap | Phase 3 INTEL-01/03 | More accurate conflict detection |
| No gap detection | Time/count-based gap trigger + targeting questions | Phase 3 GAP-01/02 | Proactive knowledge expansion |
| Single-source content storage | Content + embeddings + metadata | Phase 3 | Enables semantic search, conflict detection |

**Deferred to v2:**
- Engagement-based gap detection (INTEL-04) -- tracks how often user accesses topic, not just content count
- ML-based contradiction detection -- trains on user's accepted/rejected conflicts to improve disagreement detection
- Proactive gap research (goes out unprompted) -- per roadmap, auto-research deferred

## Open Questions

1. **What embedding dimension should we hardcode?**
   - What we know: all-MiniLM-L6-v2 produces 384-dim vectors. sqlite-vec requires dimension in table creation.
   - What's unclear: What if user wants to switch models? Dimension is baked into table schema.
   - Recommendation: Hardcode 384 as `EMBEDDING_DIMENSION` constant. Allow model swap with schema migration in v2.

2. **How to extract "key points" for disagreement presentation?**
   - What we know: Simple approach (first 3 sentences) works but isn't smart.
   - What's unclear: How to identify truly opposing claims vs. different aspects.
   - Recommendation: Use simple sentence extraction for v1. Flag "needs review" for items where disagreement isn't clear.

3. **Should gap interests be stored as preferences or separate table?**
   - What we know: Preferences have topic + approach format. Gap interests have topic + gap_description + search_query.
   - What's unclear: Are gap interests a type of preference?
   - Recommendation: Separate `gap_interests` table for now. In v2, could unify if pattern emerges.

4. **How to generate subtopic options for targeting questions?**
   - What we know: Can extract from existing content titles/summaries.
   - What's unclear: Quality of extracted subtopics without NLP.
   - Recommendation: Simple keyword extraction + hardcoded common subtopics per domain. Refine in v2.

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
| CONFLICT-01 | Conflict flagged when content overlaps on same topic with similar embedding | unit | `pytest tests/test_conflict_handler.py::test_conflict_flagged_on_overlap -x` | no |
| CONFLICT-01 | No conflict when topic differs | unit | `pytest tests/test_conflict_handler.py::test_no_conflict_different_topic -x` | no |
| CONFLICT-02 | Key disagreements presented as bullet points | unit | `pytest tests/test_conflict_handler.py::test_disagreement_presentation -x` | no |
| CONFLICT-03 | Conflict resolution updates preference profile | integration | `pytest tests/test_conflict_handler.py::test_resolution_updates_preference -x` | no |
| GAP-01 | Gap suggestion triggers after 3+ content + 24h idle | integration | `pytest tests/test_gap_handler.py::test_gap_trigger_timing -x` | no |
| GAP-01 | No gap suggestion within cooldown period | unit | `pytest tests/test_gap_handler.py::test_gap_cooldown -x` | no |
| GAP-02 | Targeting questions asked before research | unit | `pytest tests/test_gap_handler.py::test_targeting_questions_asked -x` | no |
| GAP-03 | Gap research results presented with accept/reject | unit | `pytest tests/test_gap_handler.py::test_gap_results_presentation -x` | no |
| GAP-03 | Accepted gap stored in gap_interests | integration | `pytest tests/test_gap_handler.py::test_accepted_gap_stored -x` | no |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_conflict_handler.py` -- covers CONFLICT-01, CONFLICT-02, CONFLICT-03
- [ ] `tests/test_gap_handler.py` -- covers GAP-01, GAP-02, GAP-03
- [ ] `tests/test_embedding_store.py` -- covers sqlite-vec integration
- [ ] `src/agent/handlers/conflict_handler.py` -- NEW file for conflict detection
- [ ] `src/agent/handlers/gap_handler.py` -- NEW file for gap detection
- [ ] `src/storage/embedding_store.py` -- NEW file for sqlite-vec wrapper
- [ ] `src/storage/database.py` -- add topic_metadata table, content_embeddings table, gap_interests table, vec0 extension loading

*(All Wave 0 files are new -- Phase 3 adds net-new intelligence functionality)*

## Sources

### Primary (HIGH confidence)
- sqlite-vec 0.1.7 -- https://pypi.org/project/sqlite-vec/ -- Version verified 2026-03-26
- sqlite-vec Python API -- https://alexgarcia.xyz/sqlite-vec/python.html -- Extension loading, serialization
- sqlite-vec Features -- https://alexgarcia.xyz/sqlite-vec/ -- Distance functions, virtual tables
- sentence-transformers -- https://huggingface.co/sentence-transformers -- all-MiniLM-L6-v2 model, 384-dim, CPU-friendly

### Secondary (MEDIUM confidence)
- INTEL-01 through INTEL-04 from REQUIREMENTS.md -- v2 requirements being implemented early in Phase 3
- Phase 2 existing patterns -- confirmation loop, preference storage, surfacing handler

### Tertiary (LOW confidence - not fully verified)
- Disagreement detection via opposing keyword pairs -- heuristic, may need tuning
- Gap subtopic extraction -- simple approach, may need refinement based on user feedback

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- sqlite-vec and sentence-transformers are verified packages with clear APIs
- Architecture: MEDIUM-HIGH -- sqlite-vec integration is well-documented; some async patterns need verification
- Pitfalls: MEDIUM -- embedding dimension and distance/similarity confusion are known issues documented
- Disagreement detection: MEDIUM-LOW -- keyword-based approach is simple, may not catch all conflicts

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (30 days -- sqlite-vec is pre-v1 but actively maintained; sentence-transformers is stable)
