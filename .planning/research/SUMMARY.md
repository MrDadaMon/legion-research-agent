# Project Research Summary

**Project:** Legion Research Agent
**Domain:** Persistent Personal Research Analyst Agent
**Researched:** 2026-03-26
**Confidence:** MEDIUM

## Executive Summary

The Legion Research Agent is a persistent 24/7 research analyst that stores content, learns user preferences, and surfaces relevant knowledge on demand. Experts build these systems using Python with asyncio event loops for the agent core, SQLite for structured storage with WAL mode enabled, and markdown files as a human-readable derivative. The key architectural insight is that this is a local-first, single-user system designed to run indefinitely on a Windows machine (Legion) without memory leaks or data loss.

The recommended approach prioritizes reliability and debuggability over feature richness. Core storage must use WAL mode and proper sync strategies from day one. The intelligence layer (preferences, conflict detection, gap detection) should only be added after the core intake-retrieval loop is proven. The biggest risks are SQLite locking errors (must use WAL), embedding drift when models change (must pin versions), and preference profile noise (must use explicit confirmation, not inference).

## Key Findings

### Recommended Stack

Python 3.12+ with asyncio is the core runtime -- built-in asyncio provides the agent loop with proper cancellation and concurrent handling. SQLite3 with WAL mode (not the default rollback journal) handles concurrent reads from the main loop and query handlers. For vector storage, sqlite-vec is recommended over ChromaDB for this single-user local use case -- it's lighter and co-located with content. sentence-transformers with `all-MiniLM-L6-v2` generates embeddings locally, avoiding API dependency for a 24/7 agent.

**Core technologies:**
- Python 3.12+ -- asyncio agent loop with low-overhead monitoring, proper cancellation
- SQLite3 with WAL mode -- concurrent access, source of truth for all content
- sqlite-vec -- vector embeddings stored directly in SQLite, pure C, no server needed
- sentence-transformers (all-MiniLM-L6-v2) -- fast local embedding generation
- python-dotenv -- API keys in .env, never hardcoded

### Expected Features

**Must have (table stakes):**
- Multi-format content intake -- paste any link or text, auto-detect format
- Content extraction -- transcripts for video, text for articles, parsed PDF, raw text stored
- SQLite + markdown sync storage -- SQLite source of truth, markdown human-readable backup
- Summary flow -- after intake: quick summary / full breakdown / ask question / save for later
- Content surfacing -- "what did I watch about X?" returns relevant content with context
- Explicit preference tracking -- user says "remember I liked/didn't like this because X"

**Should have (competitive differentiators):**
- Rejected approach warnings -- agent warns before exploring topics user explicitly rejected
- Conflict detection -- when two sources disagree, surface the conflict and ask user which they prefer
- Gap detection -- after 3+ pieces on a topic with 24h idle, ask if user wants more

**Defer (v2+):**
- Research on demand with targeting questions -- "find me more like this" with aspect clarification first
- Aggressive auto-tagging via LLM -- only if manual tagging proves too burdensome
- Proactive research (opt-in) -- only if user explicitly defines topics of interest

### Architecture Approach

The system uses an asyncio event loop polling every 5 seconds with sleep-based yielding (not busy-wait). Content flows through: intake handler -> extraction pipeline -> embedding generator -> brain engine (related finder, conflict detector, gap detector) -> sync manager (writes to SQLite first, then markdown). The brain is trigger-based, not continuously scanning. Project structure separates concerns: `agent/` (loop, handlers), `pipeline/` (extractors, embedding), `brain/` (intelligence), `storage/` (database, markdown, sync).

**Major components:**
1. Agent Core (loop.py) -- asyncio event loop with 5-second tick, graceful shutdown handling
2. Pipeline (extractors, embedding) -- I/O-heavy content processing, chunked for large content
3. Brain (related_finder, conflict_detector, gap_detector) -- triggered by handlers, not continuous
4. Storage (database.py, markdown_store.py, sync_manager.py) -- SQLite source of truth, markdown derived

### Critical Pitfalls

1. **SQLite Locking** -- Default rollback journal causes "database is locked" with concurrent access. Must enable WAL mode: `PRAGMA journal_mode=WAL;` and busy timeout before any multi-process work.

2. **Embedding Drift** -- If embedding model changes (provider update or model switch), old and new vectors live in different spaces and similarity becomes meaningless. Must pin model version in content metadata and build re-embedding pipeline for model changes.

3. **Preference Profile Noise/Sparse** -- Too many implicit signals floods the profile; too few explicit signals leaves it empty. Must use explicit confirmation ("should I remember that?"), signal decay (30+ days = reduced weight), and interaction-type weighting.

4. **Gap Detection Too Aggressive** -- Simple 3+ content / 24h idle threshold fires during active research sessions. Must track research session state and suppress during active intake. Higher threshold for recently-interacted topics.

5. **Markdown/SQLite Sync Drift** -- Two storage systems updated at different times causes inconsistencies. Must write both atomically (SQLite transaction + markdown), use SQLite as source of truth, verify consistency on startup.

## Implications for Roadmap

Based on research, the following phase structure addresses dependencies and prevents known pitfalls.

### Phase 1: Agent Foundation
**Rationale:** Cold start must be solved first -- a new user gets no value without onboarding. The core loop must work before adding any intelligence layer.

**Delivers:** Asyncio agent loop with wake/sleep pattern, basic SQLite storage without WAL (add in Phase 2), content intake and extraction for one format first, simple markdown sync, onboarding flow that seeds initial topics.

**Avoids:** Cold start pitfall -- onboarding with topic seeds, conservative initial surfacing.

### Phase 2: Core Storage Infrastructure
**Rationale:** Storage foundation must be solid before building intelligence. WAL mode, deduplication, chunked processing, and sync consistency are all required before concurrent access or large content.

**Delivers:** SQLite WAL mode enabled, concurrent read/write handling, content deduplication (fingerprinting), large content chunking (512-token pieces), SyncManager with transactional consistency, markdown verification on startup.

**Addresses:** Features -- multi-format intake, storage. Avoids pitfalls -- SQLite locking, markdown/sqlite drift, large content blocking, duplicate content.

### Phase 3: Intelligence Layer
**Rationale:** After stable intake-retrieval, add preference tracking and conflict detection. Gap detection deferred to v1.x (needs tuning via user feedback).

**Delivers:** Explicit preference tracking with confirmation loop, signal decay, interaction weighting; conflict detection with threshold-based overlap; rejected approach warnings at query time.

**Avoids:** Preference noise/sparse (explicit only, decay), preference misreads (require confirmation for negatives).

### Phase 4: Advanced Surfacing
**Rationale:** Core retrieval plus intelligence enables targeted research. Gap detection needs user feedback loop to tune thresholds properly.

**Delivers:** Hybrid related content (embedding + keyword with 60/40 weighting), gap detection with research session awareness, research on demand with targeting questions (aspect clarification before search).

**Avoids:** Gap detection too aggressive (suppress during active intake, configurable sensitivity).

### Phase 5: Polish and Maintenance
**Rationale:** Scale concerns emerge after 1k+ content items. Regular maintenance tasks prevent bloat.

**Delivers:** Pagination everywhere (limit 50), efficient embedding storage (BLOB not TEXT), content archival after 90 days inactive, regular VACUUM, growth monitoring.

**Avoids:** Memory bloat, search latency degradation.

### Phase Ordering Rationale

- Phase 1 before 2 -- core loop must work; storage patterns are well-established, add complexity incrementally
- Phase 2 stabilizes storage -- WAL, sync, chunking, deduplication are architectural foundations that affect everything downstream
- Phase 3 adds intelligence only after storage is reliable -- preferences and conflicts depend on clean data
- Phase 4 extends surfacing -- gap detection needs real user feedback to tune
- Phase 5 addresses scale -- wait until actual usage reveals bottlenecks

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** sqlite-vec vs BLOB for embeddings -- need to validate performance at 1k+ items during implementation
- **Phase 3:** Conflict detection threshold (0.85 similarity) is heuristic -- needs validation against real content
- **Phase 4:** Gap detection algorithm (3+ content / 24h) -- needs tuning feedback loop; Windows Task Scheduler vs service for 24/7 operation

Phases with standard patterns (skip research-phase):
- **Phase 1:** Asyncio event loop patterns are well-documented; Python 3.12 has excellent asyncio support
- **Phase 2:** SQLite WAL, deduplication, chunking -- established patterns with clear implementation guidance
- **Phase 5:** Pagination, archival, VACUUM -- standard SQLite maintenance, no research needed

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Python/asyncio/SQLite are well-documented (HIGH); sqlite-vec is newer pre-v1 with possible breaking changes |
| Features | MEDIUM | Training data knowledge of PKM/AI agent landscape; no web search verification during research |
| Architecture | MEDIUM | Established asyncio patterns from skills; WebSearch unavailable during research, validated via training data |
| Pitfalls | MEDIUM | SQLite, embeddings, preferences -- well-known domain issues from RAG and PKM literature |

**Overall confidence:** MEDIUM

### Gaps to Address

- **sqlite-vec stability:** Pre-v1 package, breaking changes possible. Verify version pinning strategy during Phase 2 implementation.
- **Embedding model selection:** `all-MiniLM-L6-v2` recommended for speed; larger model (`all-mpnet-base-v2`) may be worth testing if search quality is poor. Add comparison test during Phase 4.
- **Windows 24/7 operation:** Task Scheduler vs Python script with auto-restart vs Windows service -- recommend Task Scheduler for simplicity but need to validate on Legion.
- **YouTube transcript API variability:** Extraction research flagged this as medium complexity -- may need multiple fallback APIs.

## Sources

### Primary (HIGH confidence)
- Python 3.12 Whats New -- docs.python.org/3/whatsnew/3.12.html -- asyncio, exception handling, recursion
- sqlite3 Python docs -- docs.python.org/3/library/sqlite3.html -- WAL mode, Row factory, autocommit
- asyncio docs -- docs.python.org/3/library/asyncio.html -- event loop, queues, cancellation

### Secondary (MEDIUM confidence)
- sqlite-vec GitHub -- github.com/asg017/sqlite-vec -- vector storage in SQLite
- sentence-transformers -- HuggingFace -- local embedding generation
- Continuous Learning v2.1 skill -- confidence scoring, instinct-based patterns
- Python-patterns skill -- asyncio, dataclasses, error handling
- Pitfalls research -- RAG systems, PKM literature, SQLite best practices

### Tertiary (LOW confidence)
- Feature landscape -- training data knowledge of AI agent landscape, should verify with user research
- Competitive analysis -- Readwise, Notion, Obsidian feature comparisons, no web search verification
- Gap detection thresholds -- 3+ content / 24h idle is initial heuristic, needs tuning

---
*Research completed: 2026-03-26*
*Ready for roadmap: yes*
