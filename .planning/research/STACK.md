# Stack Research

**Domain:** Persistent Research Analyst Agent
**Researched:** 2026-03-26
**Confidence:** MEDIUM

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Agent runtime | Built-in asyncio for agent loops, improved exception handling, low-overhead monitoring (PEP 669), better recursion protection for long-running processes |
| sqlite3 | (built-in) | Primary database | Native Python, zero-config, reliable, Row factories for named access, PEP 249 compliant autocommit control, works everywhere |
| python-dotenv | 1.0+ | Environment variables | Standard for loading .env files, follows 12-factor app principles, never hardcode API keys |
| asyncio | (built-in) | Agent loop | Native async/await, built-in queues for work distribution, Event/Lock for synchronization, proper cancellation handling |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tiktoken | 0.7+ | Token counting/encoding | When you need to count tokens before sending to LLM APIs, estimate costs, or split content by token boundaries |
| sqlite-vec | 0.1+ | Vector embeddings in SQLite | **Recommended** for storing content embeddings directly in SQLite. Pure C, no dependencies, runs on Windows, float/int8/binary vectors, KNN search via MATCH |
| sentence-transformers | 3+ | Generate embeddings | When you need to create embeddings locally. Use with a lightweight model like `all-MiniLM-L6-v2` for speed |
| ChromaDB | 0.5+ | Vector database (alt) | If you want a dedicated vector DB with client-server mode. More features than sqlite-vec but heavier weight |
| FAISS | 1.8+ | Vector similarity (alt) | If you need GPU acceleration for millions of vectors. Steeper learning curve but exceptional speed at scale |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Package manager | Fast Python package manager, drop-in pip replacement, handles environments |
| pdb | Debugger | Built-in, use with Python 3.12 improved multi-threaded debugging support |
| pytest | Testing | Standard Python testing, use with pytest-asyncio for async agent tests |

## Installation

```bash
# Core dependencies
pip install python-dotenv tiktoken sentence-transformers

# Vector storage (pick one)
pip install sqlite-vec      # Recommended: SQLite-native, lightweight
# OR
pip install chromadb        # Alternative: more features, heavier

# Optional: for Windows-specific scheduling
pip install pywin32         # For Windows service integration on Legion
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|------------------------|
| sqlite-vec | ChromaDB | When you need client-server mode, more advanced filtering, or will scale to millions of embeddings |
| sqlite-vec | FAISS | When you have GPU available and need to search billions of vectors |
| asyncio loop | threading | threading is simpler for CPU-bound agents; asyncio is better for IO-bound wait-heavy agents |
| sentence-transformers | OpenAI embeddings | When you prefer API-based embeddings and cost is acceptable; local is better for 24/7 local agent |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| PostgreSQL + pgvector | Overkill for single-user local app, adds deployment complexity | sqlite-vec |
| Redis | Not designed for this use case, adds infrastructure | SQLite + sqlite-vec |
| LangChain | Overly complex abstraction layer, adds debugging difficulty | Direct API calls, keep it simple |
| SQLAlchemy | Adds ORM overhead for what SQLite handles natively | Direct sqlite3 with Row factory |
| threading + while True loop | No clean shutdown, hard to pause/resume, no async benefits | asyncio agent loop |
| global state | Makes testing harder, hidden coupling | Dataclass state passed through loop |

## Stack Patterns by Variant

**If embeddings are kept local (offline-first):**
- Use sentence-transformers with `all-MiniLM-L6-v2` model
- Use sqlite-vec for storage (co-located with content)
- No API dependency for core functionality

**If embedding quality matters more than speed:**
- Use a larger sentence-transformers model like `all-mpnet-base-v2`
- Accept slower ingestion, better similarity search

**If Windows service is needed (Legion 24/7):**
- Use pywin32 for Windows service integration
- Or use Task Scheduler to restart the script periodically
- asyncio loop with proper cancellation handles graceful shutdown

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| python-dotenv@1.0+ | Python 3.8+ | Current standard, no breaking changes expected |
| tiktoken@0.7+ | Python 3.8+ | OpenAI-maintained, stable API |
| sentence-transformers@3.0+ | Python 3.8+, PyTorch 2.0+ | Heavy dependency but well-maintained |
| sqlite-vec@0.1+ | Python 3.8+, SQLite 3.41+ | Pre-v1, breaking changes possible; check releases |
| ChromaDB@0.5+ | Python 3.8+ | Actively developed, client-server mode available |

## SQLite Schema Pattern for Research Agent

```sql
-- Content storage (core table)
CREATE TABLE content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,  -- 'youtube', 'article', 'pdf', 'text', 'paper'
    source_url TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    content_hash TEXT UNIQUE,   -- detect duplicates
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT
);

-- Full text stored as markdown file (path reference)
-- content.id -> stored in /knowledge/content/{id}.md

-- Topics (hierarchical)
CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES topics(id),
    created_at TEXT DEFAULT (datetime('now'))
);

-- Content -> Topic mapping
CREATE TABLE content_topics (
    content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (content_id, topic_id)
);

-- User preferences (positive/negative signals)
CREATE TABLE preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
    signal TEXT NOT NULL,       -- 'liked', 'rejected', 'preferred_a', 'preferred_b'
    reason TEXT,
    context TEXT,               -- what the user was trying to do at the time
    created_at TEXT DEFAULT (datetime('now'))
);

-- Rejected approaches (for conflict/warning detection)
CREATE TABLE rejected_approaches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approach_key TEXT NOT NULL,  -- hash of the rejected approach
    description TEXT,
    reason TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Embeddings stored separately (for sqlite-vec integration)
-- Virtual table created with: CREATE VIRTUAL TABLE embeddings USING vec0(...)

-- Indexes
CREATE INDEX idx_content_created ON content(created_at);
CREATE INDEX idx_content_hash ON content(content_hash);
CREATE INDEX idx_topics_name ON topics(name);
CREATE INDEX idx_preferences_content ON preferences(content_id);
CREATE INDEX idx_rejected_key ON rejected_approaches(approach_key);
```

## Agent Loop Architecture Pattern

```python
import asyncio
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class AgentState:
    messages: list = field(default_factory=list)
    iteration: int = 0
    running: bool = True
    preferences_loaded: bool = False

async def agent_loop(
    state: AgentState,
    process_fn: Callable,  # Called each iteration
    stop_event: asyncio.Event,
    poll_interval: float = 1.0
):
    """
    Persistent agent loop with graceful shutdown.
    """
    while not stop_event.is_set():
        try:
            state.iteration += 1
            await process_fn(state)
            await asyncio.sleep(poll_interval)  # Yield control, check periodically
        except asyncio.CancelledError:
            state.running = False
            raise
        except Exception as e:
            # Log error, continue running
            print(f"Error in iteration {state.iteration}: {e}")

async def main():
    stop_event = asyncio.Event()
    state = AgentState()

    agent = asyncio.create_task(agent_loop(state, process_content, stop_event))

    # Run until told to stop
    await stop_event.wait()

    agent.cancel()
    try:
        await agent
    except asyncio.CancelledError:
        pass
```

## Sources

- Python 3.12 Whats New — https://docs.python.org/3/whatsnew/3.12.html — HIGH
- sqlite3 Python docs — https://docs.python.org/3/library/sqlite3.html — HIGH
- asyncio docs — https://docs.python.org/3/library/asyncio.html — HIGH
- python-dotenv PyPI — https://pypi.org/project/python-dotenv/ — MEDIUM
- tiktoken GitHub — https://github.com/openai/tiktoken — MEDIUM
- sqlite-vec GitHub — https://github.com/asg017/sqlite-vec — MEDIUM
- ChromaDB GitHub — https://github.com/chroma-core/chroma — MEDIUM
- FAISS GitHub — https://github.com/facebookresearch/faiss — MEDIUM

---
*Stack research for: Persistent Research Analyst Agent*
*Researched: 2026-03-26*
