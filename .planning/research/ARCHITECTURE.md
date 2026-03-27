# Architecture Research

**Domain:** Persistent research analyst agent with memory
**Researched:** 2026-03-26
**Confidence:** MEDIUM

Note: WebSearch was unavailable during this research cycle. Findings are based on established patterns from training data and relevant skills (continuous-learning-v2, python-patterns). Recommendations should be validated during implementation.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AGENT CORE (main.py)                         │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Event Loop  │  │   Ingestion  │  │   Brain      │              │
│  │  (asyncio)   │  │   Handler    │  │   Engine     │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│  ┌──────┴─────────────────┴─────────────────┴───────┐              │
│  │                    BUS / MESSAGE QUEUE            │              │
│  └──────┬─────────────────┬─────────────────┬───────┘              │
│         │                 │                 │                       │
├─────────┴─────────────────┴─────────────────┴───────────────────────┤
│                        PROCESSORS                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Extractor   │  │  Embedding   │  │  Analyzer    │              │
│  │  Pipeline    │  │  Generator   │  │  (related,   │              │
│  │              │  │              │  │  conflicts)  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
├─────────────────────────────────────────────────────────────────────┤
│                        STORAGE LAYER                                │
│  ┌──────────────────────────────┐  ┌──────────────────────────┐   │
│  │         SQLite               │  │     Markdown Files       │   │
│  │  (content, topics, prefs)    │  │  (human-readable cache)  │   │
│  └──────────────────────────────┘  └──────────────────────────┘   │
│              ↕                              ↕                       │
│         [sync manager]              [sync manager]                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Recommended Project Structure

```
src/
├── main.py                    # Entry point, asyncio event loop
├── config.py                  # Environment config (.env loader)
├── agent/
│   ├── __init__.py
│   ├── loop.py                # Main event loop (wake/sleep pattern)
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── content_handler.py # Routes incoming content to pipeline
│   │   ├── query_handler.py   # Responds to "find me more like X"
│   │   └── preference_handler.py
│   └── events.py              # Event type definitions
├── pipeline/
│   ├── __init__.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── video_extractor.py  # Uses video-to-knowledge MCP
│   │   ├── article_scraper.py  # URL content extraction
│   │   └── pdf_parser.py       # PDF text extraction
│   ├── embedding.py           # Generate embeddings for content
│   └── chunker.py             # Chunk large content for processing
├── brain/
│   ├── __init__.py
│   ├── related_finder.py       # Embedding + keyword hybrid search
│   ├── conflict_detector.py   # Detect conflicting sources
│   ├── gap_detector.py        # 3+ pieces same topic + 24h idle
│   └── preference_tracker.py  # Explicit preference signals
├── storage/
│   ├── __init__.py
│   ├── database.py            # SQLite connection + migrations
│   ├── markdown_store.py      # Write/read markdown files
│   └── sync_manager.py        # SQLite <-> Markdown sync
├── models/
│   ├── __init__.py
│   ├── content.py             # ContentItem dataclass
│   ├── topic.py               # Topic dataclass
│   └── preference.py          # Preference dataclass
└── utils/
    ├── __init__.py
    └── logging.py             # Structured logging setup
```

### Structure Rationale

- **agent/**: Core agent logic - event loop, handlers, events. Separated from pipeline because handlers are the "what triggers work" and pipeline is "how work is done."
- **pipeline/**: Content extraction and embedding. These are I/O-heavy, may use MCP tools, and should be independently testable.
- **brain/**: Intelligence layer - only runs when triggered by handlers. No periodic background scanning (proactive research is deferred).
- **storage/**: Single responsibility - database.py handles SQLite, markdown_store.py handles files, sync_manager.py keeps them in sync.
- **models/**: Pure dataclasses, no logic. These are the data shape contracts.

---

## Architectural Patterns

### Pattern 1: Asyncio Event Loop with Wake/Sleep

**What:** A persistent loop that uses `asyncio.sleep()` to avoid busy-waiting, checking for new work on each iteration.

**When to use:** Always, for a 24/7 agent on Windows.

**Trade-offs:**
- Pro: Low CPU usage (sleeps between checks)
- Pro: Simple to understand and debug
- Pro: Can run indefinitely on Windows without watchdog
- Con: Latency between content arrival and processing (depends on sleep interval)

**Example:**
```python
async def run_loop(agent):
    while True:
        try:
            # Check for incoming content
            content = await agent.inbox.get_nowait()
            if content:
                await agent.process_content(content)

            # Check gap detection timer
            await agent.brain.check_gaps()

        except Exception as e:
            agent.log_error(e)

        await asyncio.sleep(5)  # 5-second tick interval
```

**Why not `while True` with `time.sleep`?** `asyncio.sleep` yields control to the event loop, allowing other coroutines to run. On Windows, `time.sleep` blocks the entire thread. With asyncio, the agent can handle multiple concurrent operations (extracting a video while responding to a query).

### Pattern 2: Write-Through Cache (SQLite <-> Markdown)

**What:** All writes go to SQLite first, then immediately to markdown. Reads prefer SQLite (fast) with markdown as fallback.

**When to use:** When you need fast queries AND human-readable files.

**Trade-offs:**
- Pro: Fast query performance via SQLite
- Pro: Human-readable backup/archive via markdown
- Pro: SQLite is the source of truth, markdown is derived
- Con: Write latency is doubled (must update both)
- Con: Sync drift risk if process crashes between writes

**Example:**
```python
class SyncManager:
    def write_content(self, item: ContentItem):
        # 1. Write to SQLite (source of truth)
        self.db.insert_content(item)
        # 2. Write to markdown (derived)
        self.markdown_store.save(item)

    def read_content(self, content_id: str) -> ContentItem | None:
        # Try SQLite first
        item = self.db.get_content(content_id)
        if item is None:
            # Fallback to markdown (recovery scenario)
            item = self.markdown_store.load(content_id)
            if item:
                self.db.insert_content(item)  # Reconcile
        return item
```

### Pattern 3: Queue-Based Content Ingestion

**What:** Incoming content is validated and queued immediately, then processed asynchronously. Large content is chunked before queuing.

**When to use:** When content arrives unpredictably and may vary in size.

**Trade-offs:**
- Pro: Immediate acknowledgment to user ("I've got it, processing...")
- Pro: Backpressure handling via queue size limits
- Pro: Large content doesn't block small content
- Con: Processing order not guaranteed (use priority queue if order matters)

**Content size handling:**
- **Small (< 100KB text, < 5 min video):** Extract immediately, no chunking
- **Large (100KB-10MB text, 5-60 min video):** Chunk into 10K-token pieces, process each, merge results
- **Very large (> 10MB, > 60 min):** Process in priority order, warn user about delay

### Pattern 4: Hybrid Related Content Detection

**What:** Use both embedding similarity AND keyword matching. Combine scores with weighted ranking.

**When to use:** When you need both semantic relatedness and topical precision.

**Trade-offs:**
- Pro: Embeddings catch semantically similar content (different words, same meaning)
- Pro: Keywords catch exact topic matches that embeddings might miss
- Pro: Flexible weighting (can tune based on false positive rate)
- Con: Two systems to maintain
- Con: Embedding generation adds latency on intake

**Scoring formula:**
```
final_score = (embedding_score * 0.6) + (keyword_score * 0.4)
```

**Threshold:** Mark as "related" when `final_score > 0.7`. Flag for conflict detection when same topic has `final_score > 0.85` but different conclusions.

---

## SQLite Schema

### Core Tables

```sql
-- content: Every piece of ingested content
CREATE TABLE content (
    id TEXT PRIMARY KEY,           -- UUID
    source_type TEXT NOT NULL,     -- 'video', 'article', 'pdf', 'text', 'book'
    source_url TEXT,               -- NULL for raw text
    title TEXT,
    summary TEXT,
    full_text TEXT,                -- Extracted text (chunked if large)
    chunk_count INTEGER DEFAULT 1,
    ingested_at TEXT NOT NULL,     -- ISO timestamp
    processed_at TEXT,             -- NULL if still processing
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'complete', 'failed'
    embedding_id TEXT,             -- FK to embeddings, NULL until generated
    metadata JSON                  -- source-specific (duration, author, etc.)
);

-- topics: User-defined or auto-detected topics
CREATE TABLE topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    parent_id TEXT REFERENCES topics(id),  -- For hierarchy
    content_count INTEGER DEFAULT 0
);

-- content_topics: Many-to-many relationship
CREATE TABLE content_topics (
    content_id TEXT REFERENCES content(id) ON DELETE CASCADE,
    topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
    confidence REAL DEFAULT 1.0,  -- How sure we are this belongs
    PRIMARY KEY (content_id, topic_id)
);

-- preferences: Explicit user signals
CREATE TABLE preferences (
    id TEXT PRIMARY KEY,
    content_id TEXT REFERENCES content(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL,     -- 'liked', 'rejected', 'comparison_winner', 'comparison_loser'
    reason TEXT,                   -- User-provided reason (optional)
    created_at TEXT NOT NULL,
    context TEXT                  -- Why this was recorded (conversation snippet)
);

-- rejections: Stamped rejections with topic + approach tracking
CREATE TABLE rejections (
    id TEXT PRIMARY KEY,
    content_id TEXT REFERENCES content(id) ON DELETE SET NULL,
    topic TEXT NOT NULL,           -- The topic being rejected
    approach TEXT,                 -- Specific approach/subject within topic
    reason TEXT,
    created_at TEXT NOT NULL
);

-- embeddings: Vector embeddings for content
CREATE TABLE embeddings (
    id TEXT PRIMARY KEY,
    content_id TEXT REFERENCES content(id) ON DELETE CASCADE,
    chunk_index INTEGER DEFAULT 0,  -- 0 for full content, 1-N for chunks
    model TEXT NOT NULL,            -- 'sentence-transformers/all-MiniLM-L6-v2'
    vector BLOB NOT NULL,           -- Stored as blob (use sqlite-vector or numpy)
    created_at TEXT NOT NULL
);

-- gap_alerts: Tracks gap detection state
CREATE TABLE gap_alerts (
    id TEXT PRIMARY KEY,
    topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
    content_count INTEGER NOT NULL,
    first_content_at TEXT NOT NULL,
    last_content_at TEXT NOT NULL,
    alerted_at TEXT,
    dismissed INTEGER DEFAULT 0
);

-- indexes for common queries
CREATE INDEX idx_content_status ON content(status);
CREATE INDEX idx_content_ingested ON content(ingested_at);
CREATE INDEX idx_topics_slug ON topics(slug);
CREATE INDEX idx_preferences_content ON preferences(content_id);
CREATE INDEX idx_rejections_topic ON rejections(topic);
CREATE INDEX idx_embeddings_content ON embeddings(content_id);
```

### Why These Tables

| Table | Purpose |
|-------|---------|
| `content` | Single source of truth for all ingested material |
| `topics` | Hierarchical taxonomy, content_count denormalized for quick listing |
| `content_topics` | Many-to-many with confidence, allows "maybe this is about X" |
| `preferences` | Explicit signals tied to content, not topics (more precise) |
| `rejections` | Stamped by topic + approach, enables "you rejected this before" |
| `embeddings` | Per-chunk vectors, enables chunk-level similarity search |
| `gap_alerts` | State machine for gap detection, avoids re-scanning |

---

## Data Flow

### Content Intake Flow

```
[User Pastes Content]
        |
        v
[Content Handler] --> validate --> [enqueue to inbox]
        |
        | (async, non-blocking)
        v
[Extractor Pipeline]
  - Detect source type (video/article/pdf/text)
  - Extract content + metadata
  - Chunk if large
        |
        v
[Embedding Generator]
  - Generate vectors for each chunk
  - Store in embeddings table
        |
        v
[Brain Engine]
  - Find related content (hybrid search)
  - Check for conflicts
  - Update topic counts
  - Check gap detection
        |
        v
[Sync Manager]
  - Write to SQLite
  - Write to Markdown file
        |
        v
[User Prompt: "summarize / ask question / save for later"]
```

### Query/Surfacing Flow

```
[User Asks About Topic]
        |
        v
[Query Handler]
  - Parse query
  - Check rejections ("you asked about X you rejected before")
        |
        v
[Brain: Related Finder]
  - Hybrid search (embeddings + keywords)
  - Rank by relevance + recency
  - Filter out rejected topics
        |
        v
[Brain: Conflict Detector]
  - If 2+ sources on same topic with different conclusions
  - Surface conflict, ask user which they prefer
        |
        v
[Response to User]
```

---

## Key Design Decisions

### 1. Persistent Loop: asyncio with polling, not event-driven

**Decision:** Use an asyncio event loop that polls every 5 seconds, not a pure event-driven architecture.

**Rationale:** For a Windows-based 24/7 agent:
- No native file watchers needed (simpler setup)
- MCP tools (video-to-knowledge, etc.) are request/response, not push
- Polling with sleep is more reliable on Windows than native async file watching
- 5-second tick is a good balance between responsiveness and CPU usage

**Anti-pattern to avoid:** `while True: time.sleep(1)` without asyncio -- blocks the thread, makes concurrent handling impossible.

### 2. Ingestion: Immediate for small, queue + chunk for large

**Decision:** Small content is processed synchronously in the loop. Large content is chunked and queued.

**Rationale:**
- Small content (short text, links) should respond in < 5 seconds
- Large content (hour-long videos, long PDFs) takes minutes -- user expects to wait, but loop shouldn't block
- Chunking enables partial results and parallel processing

### 3. Related Content: Hybrid (embeddings + keywords)

**Decision:** Use sentence-transformers embeddings for semantic similarity AND keyword matching (BM25 or TF-IDF) for exact topic matches.

**Rationale:**
- Embeddings alone can miss exact topic matches (semantic drift)
- Keywords alone miss conceptually related content (different words, same meaning)
- Hybrid with 60/40 weighting balances both

**Implementation:** Use `sentence-transformers` (all-MiniLM-L6-v2) for embeddings locally. Store vectors as BLOB in SQLite (using numpy serialization).

### 4. SQLite as Source of Truth, Markdown as Derivative

**Decision:** Write to SQLite first, then immediately to markdown. Read from SQLite, fallback to markdown only for recovery.

**Rationale:**
- SQLite is fast for queries (relevance ranking, topic aggregation)
- Markdown is human-readable for debugging, backup, manual editing
- If process crashes, markdown survives; on restart, reconcile from markdown
- Do NOT use markdown as primary -- query performance would be terrible

### 5. Explicit Preferences Only (No Inference)

**Decision:** Never infer preferences from behavior. Only record when user explicitly says "remember I liked this" or "I reject this approach."

**Rationale:** From PROJECT.md: "Explicit preference signals -- Don't infer, ask 'should I remember that?'" Inference causes false positives and erodes trust.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Busy-Wait Loop

**What people do:** `while True: time.sleep(1)` in a thread, consuming 100% CPU while "waiting."

**Why it's wrong:** Wastes CPU, causes high load on a 24/7 machine, Windows may throttle or flag the process.

**Do this instead:** `asyncio.sleep(5)` in an async loop. Yields CPU, allows concurrent operations.

### Anti-Pattern 2: Embeddings Without Chunking

**What people do:** Generate one embedding for entire content, even if it's a 2-hour video.

**Why it's wrong:** Embedding models have context windows (typically 256-512 tokens). Long content gets truncated, losing information.

**Do this instead:** Chunk content into ~512-token pieces, generate one embedding per chunk, average or max-pool for content-level similarity.

### Anti-Pattern 3: Storing Everything in Memory

**What people do:** Keep all content, embeddings, and state in Python objects.

**Why it's wrong:** Process restarts wipe state. 24/7 agents crash and restart frequently on Windows.

**Do this instead:** Persist to SQLite immediately. Memory is for working set only.

### Anti-Pattern 4: No Sync Strategy

**What people do:** Write to SQLite and markdown independently with no coordination.

**Why it's wrong:** Drift accumulates. On restart, reconciliation becomes complex. Crashes leave half-written state.

**Do this instead:** Single `SyncManager.write()` method that writes both atomically (SQLite transaction + markdown). On startup, reconcile any drift.

---

## Scaling Considerations

| Scale | Approach |
|-------|----------|
| 0-1k content items | SQLite BLOB for vectors is fine. Single file, no vector DB needed. |
| 1k-10k content items | Consider sqlite-vector extension or moving to FAISS for embedding search. |
| 10k+ content items | Move embeddings to dedicated vector DB (ChromaDB, Qdrant). SQLite remains for metadata. |

### First Bottleneck: Embedding Generation Latency

**Problem:** Generating embeddings for each intake item adds 1-5 seconds per item on CPU.

**Fix:** Use `asyncio` to run extraction and embedding concurrently. Or batch embeddings for multiple small items.

### Second Bottleneck: SQLite Query Speed with 10k+ Items

**Problem:** SQLite is fast but not infinite. Full-text search across 10k+ items in SQLite is slow.

**Fix:** Use full-text search (SQLite FTS5) for keyword matching. Use vector DB for embeddings. SQLite handles metadata only.

---

## Integration Points

### External MCP Tools

| Tool | Integration Pattern | Notes |
|------|---------------------|-------|
| video-to-knowledge | Call via MCP client in extractor pipeline | Returns transcript + summary |
| exa-search | Call for "find me more like this" queries | Use for research-on-demand |
| deep-research | Call for gap detection follow-up | Only when user confirms |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Agent loop ↔ Pipeline | asyncio Queue | Non-blocking, decoupled |
| Pipeline ↔ Storage | Direct function calls | sync_manager.write() |
| Handler ↔ Brain | Direct function calls | Brain has no async |
| Brain ↔ Storage | Direct function calls | Read-heavy |

---

## Research Gaps (Flags for Later)

The following areas need deeper investigation during implementation:

1. **Vector storage in SQLite:** Using BLOB with numpy serialization works but sqlite-vector extension (https://github.com/asg017/sqlite-vector) may be faster. Validate during implementation.

2. **Chunk size tuning:** 512 tokens is a starting point, but optimal size depends on content type (code vs prose vs transcripts). May need per-source-type chunking strategies.

3. **Gap detection algorithm:** The 3+ pieces + 24h rule is simple. May need refinement based on topic velocity (some topics accumulate faster).

4. **Conflict detection threshold:** 0.85 similarity with different conclusions is a heuristic. Need to validate against real user content.

5. **Windows service vs Python script:** For 24/7 operation on Legion, should this run as a Windows service, scheduled task, or Python script with auto-restart? Recommend Python script + Windows Task Scheduler with "on startup" trigger for simplicity.

---

## Sources

- Continuous Learning v2.1 skill (confidence scoring, instinct-based patterns)
- Python-patterns skill (asyncio, dataclasses, error handling)
- PROJECT.md (project requirements and constraints)
- Established patterns for persistent agents: asyncio event loops, write-through caching, queue-based ingestion
- Embedding strategies: sentence-transformers, hybrid search (RAG best practices)
