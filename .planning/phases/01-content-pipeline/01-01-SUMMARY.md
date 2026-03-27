---
phase: 01-content-pipeline
plan: "01"
subsystem: storage
tags: [sqlite, wal, markdown, deduplication, topics]
dependency_graph:
  requires: []
  provides:
    - STORAGE-01
    - STORAGE-02
    - STORAGE-03
    - STORAGE-04
    - STORAGE-05
  affects:
    - 01-02-PLAN (asyncio agent core)
    - 01-03-PLAN (summary flow)
tech_stack:
  added:
    - aiosqlite 0.22.1 (async SQLite)
    - pytest-asyncio 1.3.0 (async testing)
  patterns:
    - SQLite WAL mode with busy_timeout=5000
    - ContentItem/Topic dataclasses
    - Write-through cache (SQLite first, markdown second)
key_files:
  created:
    - src/models/content.py
    - src/models/topic.py
    - src/storage/database.py
    - src/storage/markdown_store.py
    - src/storage/sync_manager.py
    - tests/test_storage/test_database.py
    - tests/test_storage/test_markdown_store.py
    - tests/test_storage/test_sync_manager.py
decisions:
  - "SQLite WAL mode with PRAGMA busy_timeout=5000 for concurrent access"
  - "content_hash = SHA256(normalized_text) for deduplication"
  - "topic_slug = regex-based slugification of topic name"
  - "Markdown path: knowledge/{topic_slug}/{content_id}.md"
  - "SyncManager.write_content: SQLite first, markdown second (SQLite is source of truth)"
metrics:
  duration_minutes: 10
  completed_date: "2026-03-27"
  tasks_completed: 3
  tests_passed: 16
  commits: 3
---

# Phase 1 Plan 1: Storage Foundation Summary

## One-liner

SQLite WAL-mode storage with SHA256 deduplication, auto-created topics, and markdown sync at `knowledge/{topic}/{id}.md`.

## What Was Built

### Data Models (src/models/)

- **ContentItem** dataclass with fields: id, source_type, source_url, title, raw_content, processed_date, content_hash, reference_count
- **compute_content_hash(text)**: Collapses whitespace, returns SHA256 hex digest
- **Topic** dataclass with auto-generated slug
- **slugify(name)**: Converts topic name to URL-safe slug via regex

### SQLite Database Layer (src/storage/database.py)

- Async Database class using aiosqlite
- WAL mode: `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000`
- Foreign keys enabled with ON DELETE CASCADE
- Tables: `content`, `topics`, `content_topics` (junction), `idx_content_hash` index
- **insert_content()**: On duplicate hash, increments reference_count instead of inserting
- Full CRUD: get_content, get_all_content, content_exists_by_hash
- Topic ops: get_or_create_topic (auto-slugifies), link_content_to_topic, get_content_topics, get_topic_content

### Markdown Store (src/storage/markdown_store.py)

- Saves ContentItem as `knowledge/{topic_slug}/{id}.md`
- YAML frontmatter: id, title, source_type, source_url, topic, processed_date, content_hash, reference_count
- Markdown body: `# title` heading + raw_content
- Load, delete, list_topic_content, list_topics operations

### Sync Manager (src/storage/sync_manager.py)

- **write_content(item, topic_name)**: Writes to SQLite first, then markdown
- **reconcile()**: Returns {missing_markdown: N, missing_sqlite: N}

## Verification Results

| Check | Result |
|-------|--------|
| WAL mode enabled | wal |
| busy_timeout | 5000 |
| Duplicate hash increments reference_count | 2 |
| Markdown file created | Yes |
| 16 tests passing | Yes |

## Commits

- `96b36a2` feat: add ContentItem and Topic data models
- `eae9b83` feat: add SQLite database layer with WAL mode
- `c0f9797` feat: add markdown store and sync manager

## Success Criteria Met

- STORAGE-01: Content stored in SQLite with all required fields
- STORAGE-02: Duplicate content detected via content_hash, reference_count incremented
- STORAGE-03: Human-readable markdown file created per content item under knowledge/{topic}/
- STORAGE-04: SQLite and markdown stay in sync via SyncManager (SQLite source of truth)
- STORAGE-05: Topics auto-created via get_or_create_topic with slug auto-generated

## Self-Check: PASSED

All files exist, commits verified, tests pass.
