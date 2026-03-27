---
phase: 01-content-pipeline
plan: "02"
subsystem: pipeline
tags: [youtube, article, pdf, text, extraction, auto-detection]
dependency_graph:
  requires:
    - 01-content-pipeline-01
  provides:
    - INTAKE-01
    - INTAKE-02
    - INTAKE-03
    - INTAKE-04
    - INTAKE-05
  affects:
    - 01-03-PLAN (summary flow)
tech_stack:
  added:
    - youtube-transcript-api 1.2.4 (YouTube transcript extraction)
    - beautifulsoup4 4.14.3 (article HTML scraping)
    - requests 2.32.5 (HTTP client for article/PDF fetching)
    - PyMuPDF 1.27.2.2 (PDF text extraction)
  patterns:
    - URL regex-based content type detection
    - Async extractors with proper error handling
    - YouTubeTranscriptApi.fetch() for transcripts
    - BeautifulSoup article extraction with fallback selectors
    - PyMuPDF multi-page text extraction
key_files:
  created:
    - src/config.py
    - src/agent/__init__.py
    - src/agent/loop.py
    - src/agent/handlers/__init__.py
    - src/agent/handlers/intake_handler.py
    - src/pipeline/__init__.py
    - src/pipeline/content_detector.py
    - src/pipeline/extractors/__init__.py
    - src/pipeline/extractors/youtube_extractor.py
    - src/pipeline/extractors/article_scraper.py
    - src/pipeline/extractors/pdf_extractor.py
    - src/pipeline/extractors/text_classifier.py
    - tests/test_content_detector.py
    - tests/test_extractors/test_youtube_extractor.py
    - tests/test_extractors/test_article_scraper.py
    - tests/test_extractors/test_pdf_extractor.py
decisions:
  - "URL regex detection for content type (youtube/article/pdf/text)"
  - "YouTubeTranscriptApi.fetch() returns FetchedTranscript with .text attribute"
  - "BeautifulSoup tries article > main > class regex selectors for article body"
  - "PyMuPDF extracts text from all pages, joins with newlines"
  - "Text classifier normalizes whitespace, uses first 100 chars as title"
metrics:
  duration_minutes: 8
  completed_date: "2026-03-27"
  tasks_completed: 3
  tests_passed: 35
  commits: 3
---

# Phase 1 Plan 2: Asyncio Agent Core with Intake Handlers Summary

## One-liner

Asyncio agent loop with auto-detecting intake handlers for YouTube, article, PDF, and raw text content - all four content types now supported with proper extraction.

## What Was Built

### Config Loader (src/config.py)

- Loads from .env using python-dotenv
- KNOWLEDGE_DIR, DB_PATH, POLL_INTERVAL configurable via environment
- Auto-creates knowledge/ directory on startup

### Asyncio Agent Loop (src/agent/loop.py)

- AgentState dataclass with inbox queue, iteration counter, running flag
- run_agent() initializes Database, MarkdownStore, SyncManager
- Main loop polls inbox with asyncio.Queue.get_nowait()
- Yields with asyncio.sleep(poll_interval)
- Graceful shutdown on CancelledError or KeyboardInterrupt
- Closes database on exit

### Content Type Auto-Detector (src/pipeline/content_detector.py)

- detect_content_type() returns 'youtube', 'article', 'pdf', or 'text'
- YouTube detected via youtube.com or youtu.be in netloc
- PDF detected via .pdf extension in URL path
- Raw text detected via length, newlines, null bytes heuristics
- extract_video_id() handles both youtube.com/watch?v=ID and youtu.be/ID formats

### Four Intake Extractors (src/pipeline/extractors/)

- **youtube_extractor.py**: Uses YouTubeTranscriptApi.fetch() for transcript extraction. Returns (title, raw_transcript, video_id). Falls back to "[Transcript unavailable]" on error.
- **article_scraper.py**: Uses requests + BeautifulSoup. Tries article > main > class=regex selectors. Returns (title, text). Logs warning if content seems low quality.
- **pdf_extractor.py**: Uses PyMuPDF. Handles URL, bytes, or file path input. Extracts text from all pages. Returns (title, text).
- **text_classifier.py**: Normalizes whitespace, uses first 100 chars as title. Returns (source_type, title, processed_text).

### Intake Handler (src/agent/handlers/intake_handler.py)

- process_content() routes input to correct extractor based on auto-detected type
- Builds ContentItem with all required fields
- Stores via SyncManager.write_content()
- Returns ContentItem with id populated

## Commits

- `306228d` feat(01-content-pipeline): add config loader and asyncio agent loop
- `1b38d0d` feat(01-content-pipeline): add content type auto-detector
- `5aae029` feat(01-content-pipeline): add four intake extractors and intake handler

## Verification Results

| Check | Result |
|-------|--------|
| Content detector tests | 12 passed |
| YouTube extractor tests | 3 passed |
| Article scraper tests | 1 passed |
| PDF extractor tests | 2 passed |
| Storage tests (from 01-01) | 16 passed |
| Total tests | 35 passed |

## Success Criteria Met

- INTAKE-01: YouTube URL yields transcript via YouTubeTranscriptApi.fetch()
- INTAKE-02: Article URL yields scraped content via BeautifulSoup
- INTAKE-03: Raw text classified as 'text' type and stored correctly
- INTAKE-04: PDF text extracted via PyMuPDF from all pages
- INTAKE-05: Content type auto-detected without user prompts

## Deviations from Plan

1. **Rule 1 - Bug Fix**: YouTubeTranscriptApi API changed from get_transcript() to fetch(). Fixed extractor to use correct API. The FetchedTranscript object has .text attribute instead of returning a list.

2. **Rule 1 - Bug Fix**: PDF extractor was accessing metadata after close(). Fixed to capture metadata before closing.

3. **Rule 1 - Bug Fix**: URL regex pattern for YouTube standard URLs had incorrect regex. Fixed to correctly parse video IDs from query string.

## Self-Check: PASSED

All files exist, commits verified, tests pass.
