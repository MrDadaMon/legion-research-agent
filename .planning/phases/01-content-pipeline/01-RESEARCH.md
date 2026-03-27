# Phase 1: Content Pipeline - Research

**Researched:** 2026-03-26
**Domain:** Multi-format content intake, extraction, SQLite storage, markdown sync, summary flow
**Confidence:** MEDIUM-HIGH

## Summary

Phase 1 builds the content pipeline foundation: accepting content in any format (YouTube, article URLs, raw text, PDFs), extracting text, storing in SQLite with WAL mode, creating human-readable markdown files, and presenting a 4-option summary menu. All required packages are either already installed or have well-established implementations. The asyncio loop structure is straightforward. Content type auto-detection uses URL pattern matching. SQLite schema uses WAL mode with a single `content` table and a `topics` table with a junction table for many-to-many relationships.

**Primary recommendation:** Use `youtube-transcript-api` for YouTube (already installed), `beautifulsoup4` + `requests` for article scraping (already installed), `PyMuPDF` (already installed) for PDFs, `python-dotenv` for config (already installed), `aiosqlite` for async SQLite operations (already installed), and `click` (already installed) for the CLI quick-select menu.

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| youtube-transcript-api | 1.2.4 | YouTube transcript extraction | Pure Python, no yt-dlp dependency needed, works with most YouTube videos |
| beautifulsoup4 | 4.14.3 | HTML parsing for article scraping | Standard Python scraping library, works with any HTML |
| PyMuPDF (fitz) | 1.27.2.2 | PDF text extraction | Already installed, fast, good text extraction, handles most PDFs |
| python-dotenv | 1.2.2 | Environment variable loading | Standard for .env files, follows 12-factor app principles |
| aiosqlite | 0.22.1 | Async SQLite operations | Built on sqlite3, native async support, WAL mode compatible |
| click | 8.3.1 | CLI interface | Standard Python CLI library, used for quick-select menu |

### Missing - Need to Install
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| questionary | 2.1.1 | Interactive CLI prompts | Clean API for yes/no menus, simple integration with asyncio |
| pypdf | 6.9.2 | Secondary PDF extraction | Fallback if PyMuPDF fails on certain PDFs |

**Installation:**
```bash
pip install questionary
```

**Verification commands:**
```bash
pip index versions questionary  # Expected: 2.1.1
pip index versions pypdf        # Expected: 6.9.2
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| youtube-transcript-api | yt-dlp (installed) | yt-dlp is heavier but more robust; use as fallback if transcript API fails |
| beautifulsoup4 + requests | newspaper3k | newspaper3k bundles everything but is less actively maintained and has known Python 3.11+ issues |
| beautifulsoup4 + requests | trafilatura | Better quality extraction but adds dependency; beautifulsoup4 + requests is sufficient for v1 |
| PyMuPDF | pdfplumber | pdfplumber has better table extraction but PyMuPDF is already installed and handles basic text extraction well |
| questionary | InquirerPy | InquirerPy is more feature-rich but questionary is simpler and sufficient for a 4-option menu |
| click | argparse | argparse works but click provides better interactive prompt support |

## Architecture Patterns

### Recommended Project Structure
```
src/
├── main.py                    # Entry point, asyncio event loop
├── config.py                  # Environment config (.env loader)
├── agent/
│   ├── __init__.py
│   ├── loop.py                # Main asyncio event loop
│   └── handlers/
│       ├── __init__.py
│       ├── intake_handler.py   # Auto-detects content type, routes to extractor
│       └── summary_handler.py  # Handles quick-select menu and modes
├── pipeline/
│   ├── __init__.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── youtube_extractor.py
│   │   ├── article_scraper.py
│   │   ├── pdf_extractor.py
│   │   └── text_classifier.py
│   └── content_detector.py    # URL pattern matching for auto-detection
├── storage/
│   ├── __init__.py
│   ├── database.py            # SQLite connection, WAL mode, migrations
│   ├── markdown_store.py      # Write/read markdown files per content item
│   └── sync_manager.py        # SQLite <-> Markdown sync
└── models/
    ├── __init__.py
    ├── content.py             # ContentItem dataclass
    └── topic.py               # Topic dataclass
knowledge/                      # Markdown files organized by topic
├── tech/
│   └── {content_id}.md
├── science/
│   └── {content_id}.md
└── _topics/
    └── topics.md              # Topic index
tests/
├── conftest.py
├── test_content_detector.py
├── test_extractors/
│   ├── test_youtube_extractor.py
│   ├── test_article_scraper.py
│   └── test_pdf_extractor.py
├── test_storage/
│   ├── test_database.py
│   └── test_sync_manager.py
└── test_summary_flow.py
```

### Pattern 1: Asyncio Agent Loop with Content Queue

**What:** A persistent loop that uses `asyncio.sleep()` to yield control, checking for new work on each iteration. Content is queued via `asyncio.Queue` for non-blocking processing.

**When to use:** Always, for a 24/7 agent on Windows.

**Example (source: asyncio official docs pattern):**
```python
import asyncio
from dataclasses import dataclass, field

@dataclass
class AgentState:
    inbox: asyncio.Queue = field(default_factory=asyncio.Queue)
    iteration: int = 0
    running: bool = True

async def agent_loop(state: AgentState, poll_interval: float = 5.0):
    while state.running:
        try:
            state.iteration += 1
            # Check for incoming content (non-blocking)
            content = state.inbox.get_nowait()
            if content:
                await process_content(content)
        except asyncio.QueueEmpty:
            pass  # No content waiting
        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(poll_interval)  # Yield control, 5-second tick

async def main():
    state = AgentState()
    # Start the loop
    loop = asyncio.create_task(agent_loop(state))
    # Add content to inbox from user input
    await state.inbox.put(user_content)
    await loop
```

**Key insight:** `asyncio.sleep()` yields control to the event loop. On Windows, `time.sleep()` blocks the entire thread. With asyncio, the agent can handle multiple concurrent operations (extracting a video while responding to a query).

### Pattern 2: Content Type Auto-Detection via URL Pattern Matching

**What:** Parse the input string to determine content type before routing to the appropriate extractor.

**Example:**
```python
import re
from urllib.parse import urlparse

def detect_content_type(input_str: str) -> str:
    """Returns: 'youtube', 'article', 'pdf', or 'text'"""
    stripped = input_str.strip()

    # Check if it looks like a URL
    if stripped.startswith(('http://', 'https://')):
        parsed = urlparse(stripped)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # YouTube
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'youtube'

        # PDF
        if path.endswith('.pdf') or domain.endswith('.pdf'):
            return 'pdf'

        # Article (generic URL, not YouTube, not PDF)
        return 'article'

    # Default to raw text
    return 'text'
```

### Pattern 3: SQLite WAL Mode with Transactional Writes

**What:** Enable WAL mode on SQLite for concurrent access, use transactions for atomic writes to both SQLite and markdown.

**Example:**
```python
import sqlite3
import aiosqlite

DB_PATH = "knowledge/legion.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_url TEXT,
                title TEXT NOT NULL,
                raw_content TEXT NOT NULL,
                processed_date TEXT DEFAULT (datetime('now')),
                content_hash TEXT UNIQUE,
                reference_count INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                slug TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS content_topics (
                content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
                topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
                PRIMARY KEY (content_id, topic_id)
            )
        """)
        await db.commit()

async def insert_content(content_item: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO content (source_type, source_url, title, raw_content, content_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (
            content_item['source_type'],
            content_item.get('source_url'),
            content_item['title'],
            content_item['raw_content'],
            content_item['content_hash']
        ))
        # If INSERT OR IGNORE succeeded (hash was new), row was added
        # If it failed (hash existed), increment reference_count
        cursor = await db.execute("SELECT changes()")
        if (await cursor.fetchone())[0] == 0:
            # Duplicate - increment reference count
            await db.execute("""
                UPDATE content SET reference_count = reference_count + 1
                WHERE content_hash = ?
            """, (content_item['content_hash'],))
        await db.commit()
```

**Critical:** Always set `PRAGMA journal_mode=WAL` before any other operations. Always set `PRAGMA busy_timeout=5000` to prevent "database is locked" errors.

### Pattern 4: Markdown File Creation with Topic Organization

**What:** Each content item gets a markdown file with YAML frontmatter, organized under a topic directory.

**File path pattern:** `knowledge/{topic_slug}/{content_id}.md`

**Example:**
```markdown
---
id: 42
title: "How Transformers Work"
source_type: article
source_url: "https://example.com/article"
topic: AI/Transformers
processed_date: 2026-03-26T14:30:00
content_hash: abc123def456
---

# How Transformers Work

Full extracted content here...

## Key Points

- Point 1
- Point 2
```

### Pattern 5: Quick-Select Menu via questionary

**What:** After processing content, present 4 options and wait for user selection.

**Example:**
```python
import questionary

async def show_summary_menu(content_id: int, title: str):
    choice = await questionary.select(
        f"Content processed: **{title}**\nWhat would you like to do?",
        choices=[
            "Quick Summary",      # SUMMARY-02: 3-5 bullet points
            "Full Breakdown",     # SUMMARY-03: timestamps, quotes, questions
            "Ask a Question",    # SUMMARY-04: user types question
            "Save for Later",     # SUMMARY-05: defer processing
        ]
    ).ask_async()

    if choice == "Quick Summary":
        return await quick_summary(content_id)
    elif choice == "Full Breakdown":
        return await full_breakdown(content_id)
    elif choice == "Ask a Question":
        return await ask_question_mode(content_id)
    else:
        return await save_for_later(content_id)
```

**Important:** Use `.ask_async()` for use within an asyncio event loop.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YouTube transcript extraction | Build custom YouTube API wrapper | youtube-transcript-api | Handles auth, rate limits, caption format conversion, error cases |
| Article HTML parsing | Build custom HTML extractor | beautifulsoup4 + requests | Handles malformed HTML, encoding issues, edge cases |
| PDF text extraction | Build custom PDF parser | PyMuPDF (installed) or pypdf | PDFs are complex binary format; libraries handle fonts, layouts, encoding |
| Content type detection | Build complex ML classifier | URL pattern regex | URL structure is deterministic; no ML needed for 4 types |
| Interactive CLI prompts | Build custom input loop | questionary | Handles arrow keys, validation, async integration cleanly |
| SQLite concurrent access | Default rollback journal | WAL mode + busy_timeout | WAL allows concurrent reads during writes; default journal blocks |
| Markdown generation | String concatenation | Python format strings or jinja2 | Proper escaping, frontmatter handling |

**Key insight:** YouTube API authentication, PDF binary parsing, and HTML edge cases are all deceptively complex. Use battle-tested libraries.

## Common Pitfalls

### Pitfall 1: YouTube Transcript Unavailable
**What goes wrong:** youtube-transcript-api fails on some videos (no captions, age-restricted, region-locked).
**Why it happens:** Not all YouTube videos have auto-generated or manual captions.
**How to avoid:** Always wrap in try/except. Fall back to yt-dlp for caption extraction. Store empty transcript with `transcript_available: false` flag so user knows it was attempted.
**Warning signs:** `Could not retrieve transcripts for video ID` exception.

### Pitfall 2: SQLite "database is locked"
**What goes wrong:** Write fails with "database is locked" after a few operations.
**Why it happens:** Default rollback journal mode blocks writers; concurrent access without WAL mode.
**How to avoid:** `PRAGMA journal_mode=WAL` AND `PRAGMA busy_timeout=5000` set BEFORE any table operations. Always close cursors promptly.
**Warning signs:** `sqlite3.OperationalError: database is locked`.

### Pitfall 3: Article Scraping Returns Navigation/Boilerplate
**What goes wrong:** Scraped content includes nav menus, footers, ads instead of article body.
**Why it happens:** Generic scraping returns entire page, not article content.
**How to avoid:** Use CSS selectors for `<article>`, `<main>`, or `.content` areas. Try multiple selectors. Store empty content with flag if extraction fails.
**Warning signs:** Extracted text is very short (< 200 chars) or contains words like "navigation", "menu", "subscribe".

### Pitfall 4: Markdown/SQLite Sync Drift
**What goes wrong:** SQLite and markdown files get out of sync after a crash.
**Why it happens:** Process crashes between SQLite write and markdown write.
**How to avoid:** Write to SQLite first (source of truth). On startup, reconcile: check if all markdown files have SQLite rows and vice versa. Use transactions.
**Warning signs:** `FileExistsError` on markdown write, missing content_id in SQLite query.

### Pitfall 5: Duplicate Processing on Restart
**What goes wrong:** Content re-processed on agent restart because no persistence of processing state.
**Why it happens:** In-memory queue or incomplete processing state lost on restart.
**How to avoid:** Only add to inbox from user input. Don't re-process content already in SQLite (check content_hash before processing). Mark content status in SQLite as `pending` -> `processing` -> `complete`.

## Code Examples

### YouTube Transcript Extraction
```python
# Source: youtube-transcript-api docs (verified via pip show)
from youtube_transcript_api import YouTubeTranscriptApi

def get_youtube_transcript(video_url: str) -> tuple[str, list[dict]]:
    """Returns (transcript_text, [{"text": "...", "start": 0.0, "duration": 2.5}, ...])"""
    video_id = extract_video_id(video_url)  # Parse from URL
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    full_text = " ".join(entry["text"] for entry in transcript)
    return full_text, transcript
```

### Article Scraping
```python
# Source: beautifulsoup4 standard pattern
import requests
from bs4 import BeautifulSoup

def scrape_article(url: str) -> tuple[str, str]:
    """Returns (title, main_text)"""
    response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    # Try multiple content selectors
    article = (
        soup.find("article") or
        soup.find("main") or
        soup.find(class_=re.compile(r"content|article|post"))
    )

    title = soup.find("title").text.strip() if soup.find("title") else "Untitled"
    text = article.get_text(separator="\n", strip=True) if article else ""

    return title, text
```

### PDF Text Extraction with PyMuPDF
```python
# Source: PyMuPDF documentation
import fitz  # PyMuPDF

def extract_pdf_text(pdf_path_or_bytes) -> str:
    """Returns extracted text from PDF"""
    doc = fitz.open(pdf_path_or_bytes) if isinstance(pdf_path_or_bytes, str) else fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)
```

### Content Hash for Deduplication
```python
import hashlib

def compute_content_hash(text: str) -> str:
    """SHA256 hash of normalized text for deduplication"""
    normalized = " ".join(text.split())  # Collapse whitespace
    return hashlib.sha256(normalized.encode()).hexdigest()
```

### Quick-Select Async Menu
```python
# Source: questionary docs
import questionary

async def prompt_summary_mode() -> str:
    return await questionary.select(
        "What would you like to do?",
        choices=["Quick Summary", "Full Breakdown", "Ask a Question", "Save for Later"],
        default="Quick Summary"
    ).ask_async()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `while True: time.sleep()` blocking loop | `asyncio.sleep()` yielding loop | Python 3.4+ asyncio | Non-blocking, can handle concurrent I/O |
| Default SQLite rollback journal | WAL mode | SQLite 3.6+ | Concurrent reads during writes, no "database locked" |
| `PyPDF2` (deprecated) | `pypdf` (renamed, active) or `PyMuPDF` (installed) | PyPDF2 abandoned 2020 | Better maintenance, more features |
| `newspaper` (unmaintained) | `beautifulsoup4` + `requests` | newspaper3k has Python 3.11+ issues | More reliable, simpler dependency chain |
| `argparse` for interactive prompts | `questionary` | Modern CLI patterns | Cleaner async API, better UX |

**Deprecated/outdated:**
- `PyPDF2`: Renamed to `pypdf`. Do not use `PyPDF2` package (deprecated).
- `newspaper3k`: Has known Python 3.11+ compatibility issues. Use beautifulsoup4 directly.
- `time.sleep()` in asyncio code: Blocks entire thread. Always use `asyncio.sleep()`.

## Open Questions

1. **Should yt-dlp be used as primary YouTube extractor instead of youtube-transcript-api?**
   - What we know: youtube-transcript-api is simpler but fails on some videos. yt-dlp is installed and more robust.
   - What's unclear: Whether the added complexity of yt-dlp is worth the reliability gain for Phase 1.
   - Recommendation: Start with youtube-transcript-api as primary, use yt-dlp as fallback. Keep it simple for Phase 1.

2. **Should article scraping use trafilatura instead of beautifulsoup4?**
   - What we know: trafilatura provides better quality extraction (removes boilerplate automatically) but adds a dependency.
   - What's unclear: Whether beautifulsoup4 + manual selectors is sufficient for Phase 1 or if quality will be frustrating.
   - Recommendation: Try beautifulsoup4 first. Add trafilatura in Phase 2 if scraping quality is poor.

3. **How to handle very large content (hour-long videos, 500+ page PDFs)?**
   - What we know: STORAGE-01 requires raw_content field; chunking is deferred to Phase 2 per SUMMARY research.
   - What's unclear: Whether a 500-page PDF will cause memory/time issues in Phase 1.
   - Recommendation: Process but warn user about long processing time. Add streaming/chunking in Phase 2 if needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 0.26.0 |
| Config file | `pytest.ini` or `pyproject.toml` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| INTAKE-01 | YouTube URL -> transcript extracted | unit | `pytest tests/test_extractors/test_youtube_extractor.py -x` | no |
| INTAKE-02 | Article URL -> main content scraped | unit | `pytest tests/test_extractors/test_article_scraper.py -x` | no |
| INTAKE-03 | Raw text -> classified and stored | unit | `pytest tests/test_extractors/test_text_classifier.py -x` | no |
| INTAKE-04 | PDF -> text extracted | unit | `pytest tests/test_extractors/test_pdf_extractor.py -x` | no |
| INTAKE-05 | Auto-detect content type from input | unit | `pytest tests/test_content_detector.py -x` | no |
| STORAGE-01 | SQLite stores all required fields | integration | `pytest tests/test_storage/test_database.py -x` | no |
| STORAGE-02 | Duplicate via content_hash, reference_count++ | integration | `pytest tests/test_storage/test_database.py -x` | no |
| STORAGE-03 | Markdown file created per content item | integration | `pytest tests/test_storage/test_markdown_store.py -x` | no |
| STORAGE-04 | SQLite and markdown in sync | integration | `pytest tests/test_storage/test_sync_manager.py -x` | no |
| STORAGE-05 | Topics auto-created | unit | `pytest tests/test_storage/test_database.py -x` | no |
| SUMMARY-01 | 4-option menu appears after processing | integration | `pytest tests/test_summary_flow.py -x` | no |
| SUMMARY-02 | Quick Summary returns 3-5 bullets | unit | `pytest tests/test_summary_flow.py::test_quick_summary -x` | no |
| SUMMARY-03 | Full Breakdown returns structure | unit | `pytest tests/test_summary_flow.py::test_full_breakdown -x` | no |
| SUMMARY-04 | Ask a Question mode works | unit | `pytest tests/test_summary_flow.py::test_ask_question -x` | no |
| SUMMARY-05 | Save for Later defers processing | unit | `pytest tests/test_summary_flow.py::test_save_for_later -x` | no |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` -- shared fixtures (db_path, sample_content, event_loop)
- [ ] `tests/test_extractors/test_youtube_extractor.py` -- covers INTAKE-01
- [ ] `tests/test_extractors/test_article_scraper.py` -- covers INTAKE-02
- [ ] `tests/test_extractors/test_pdf_extractor.py` -- covers INTAKE-04
- [ ] `tests/test_content_detector.py` -- covers INTAKE-05
- [ ] `tests/test_storage/test_database.py` -- covers STORAGE-01, STORAGE-02, STORAGE-05
- [ ] `tests/test_storage/test_markdown_store.py` -- covers STORAGE-03
- [ ] `tests/test_storage/test_sync_manager.py` -- covers STORAGE-04
- [ ] `tests/test_summary_flow.py` -- covers SUMMARY-01 through SUMMARY-05
- [ ] `pytest.ini` or update `pyproject.toml` -- pytest-asyncio configuration
- [ ] Framework install: `pip install pytest-asyncio questionary` (if not present)

*(No existing test infrastructure -- all Wave 0 files need to be created)*

## Sources

### Primary (HIGH confidence)
- youtube-transcript-api PyPI -- https://pypi.org/project/youtube-transcript-api/ -- version 1.2.4, installed
- beautifulsoup4 PyPI -- https://pypi.org/project/beautifulsoup4/ -- version 4.14.3, installed
- PyMuPDF (fitz) -- https://pypi.org/project/PyMuPDF/ -- version 1.27.2.2, installed
- python-dotenv PyPI -- https://pypi.org/project/python-dotenv/ -- version 1.2.2, installed
- aiosqlite PyPI -- https://pypi.org/project/aiosqlite/ -- version 0.22.1, installed
- click PyPI -- https://pypi.org/project/click/ -- version 8.3.1, installed
- sqlite3 Python docs -- https://docs.python.org/3/library/sqlite3.html -- WAL mode, Row factory, autocommit
- asyncio docs -- https://docs.python.org/3/library/asyncio.html -- event loop, queues, cancellation

### Secondary (MEDIUM confidence)
- pypdf PyPI -- https://pypi.org/project/pypdf/ -- version 6.9.2, not installed but recommended fallback
- questionary PyPI -- https://pypi.org/project/questionary/ -- version 2.1.1, not installed
- youtube-transcript-api GitHub -- https://github.com/jdepoix/youtube-transcript-api -- API patterns
- beautifulsoup4 documentation -- https://www.crummy.com/software/BeautifulSoup/bs4/doc/ -- selector patterns

### Tertiary (LOW confidence - not verified, based on training data)
- URL pattern matching for content type detection -- standard regex patterns, no specific authoritative source
- PyMuPDF text extraction patterns -- general PDF library usage, may need verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages verified via pip, versions confirmed
- Architecture: MEDIUM -- asyncio patterns well-established; URL detection and markdown organization are straightforward
- Pitfalls: MEDIUM -- known SQLite and scraping issues documented; YouTube transcript edge cases flagged
- Content detection: MEDIUM -- regex URL patterns are standard but need validation against real URLs

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (30 days -- stable domain, library versions checked)
