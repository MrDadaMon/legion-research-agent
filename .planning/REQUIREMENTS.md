# Requirements: Legion Research Agent

**Defined:** 2026-03-26
**Core Value:** You stop re-watching videos to find one thing you vaguely remember. Everything you've ever sent it is searchable, comparable, and alive in your conversations.

## v1 Requirements

### Intake & Extraction

- [ ] **INTAKE-01**: User can paste a YouTube URL and agent extracts the transcript
- [ ] **INTAKE-02**: User can paste an article URL and agent scrapes the main content
- [ ] **INTAKE-03**: User can paste raw text and agent classifies and stores it
- [ ] **INTAKE-04**: User can attach or paste PDF content and agent extracts text
- [ ] **INTAKE-05**: Agent auto-detects content type without asking user

### Storage

- [x] **STORAGE-01**: Content stored in SQLite with fields: id, source_type, source_url, title, raw_content, processed_date, content_hash
- [x] **STORAGE-02**: Duplicate content detected via content_hash, reference_count incremented
- [x] **STORAGE-03**: Human-readable markdown file created per content item, organized by auto-detected topic
- [x] **STORAGE-04**: SQLite and markdown files kept in sync (SQLite is source of truth)
- [x] **STORAGE-05**: Topics auto-created and merged as patterns emerge

### Summary Flow

- [x] **SUMMARY-01**: After processing content, agent presents 4-option quick-select: Quick Summary / Full Breakdown / Ask a Question / Save for Later
- [x] **SUMMARY-02**: Quick Summary returns 3-5 key points in bullet format
- [x] **SUMMARY-03**: Full Breakdown returns structured notes: timestamps, key quotes, follow-up questions
- [x] **SUMMARY-04**: "Ask a Question" mode lets user type a question about the content
- [x] **SUMMARY-05**: "Save for Later" defers processing, stores URL for future retrieval

### Preference Tracking

- [x] **PREF-01**: After comparison, agent asks "Should I remember that you prefer X over Y?" before updating profile
- [x] **PREF-02**: Rejections stored with: topic, approach, reason, date, source content
- [x] **PREF-03**: Preference profile human-readable and rewriteable (not just append)
- [x] **PREF-04**: Rejected approach warning fires when user mentions or uses a rejected approach

### Content Surfacing

- [x] **SURFACE-01**: User can ask "what do I have on X?" and agent returns relevant content with sources
- [x] **SURFACE-02**: Agent proactively surfaces relevant knowledge during conversations when context matches
- [x] **SURFACE-03**: Each surfacing includes source URL, date, and brief description

### Conflict Detection

- [x] **CONFLICT-01**: When new content overlaps with existing content on same topic, agent flags potential conflict
- [x] **CONFLICT-02**: Agent presents key points of disagreement between conflicting sources
- [x] **CONFLICT-03**: User resolves conflict by choosing preferred approach, which updates preference profile

### Gap Detection

- [x] **GAP-01**: After 3+ pieces of content on same topic with 24h+ idle, agent suggests gap exploration
- [x] **GAP-02**: Agent asks targeting questions before initiating gap research
- [x] **GAP-03**: Gap research results presented for user to decide whether to incorporate

### Research on Demand

- [ ] **RESEARCH-01**: User can say "find me more like this" on any stored content
- [ ] **RESEARCH-02**: Agent asks 1-2 targeting questions before searching
- [ ] **RESEARCH-03**: Results returned with citations, source URLs, and relevance explanation

## v2 Requirements

### Intelligence Layer

- **INTEL-01**: Hybrid search combining embeddings (60%) + keyword matching (40%) for related content detection
- **INTEL-02**: Embeddings stored via sqlite-vec for fast vector similarity queries
- **INTEL-03**: Conflict detection using cosine similarity threshold (0.85 heuristic)
- **INTEL-04**: Gap detection considers user engagement patterns, not just content count

### Persistence & Operations

- **OPS-01**: Agent runs as Windows Task Scheduler job with auto-restart on Legion
- **OPS-02**: Health heartbeat logged every 5 minutes
- **OPS-03**: Nightly SQLite backup to cloud storage
- **OPS-04**: Periodic VACUUM to prevent database bloat

### Communication Layer

- **COMM-01**: Discord integration for remote communication via phone
- **COMM-02**: Cloudflare tunnel for Legion remote access
- **COMM-03**: Multiple agents share single Discord inbox with self-selection routing

## Out of Scope

| Feature | Reason |
|---------|--------|
| Proactive research (goes out unprompted) | Core storage/surfacing must be solid first |
| Multi-user support | Single user v1 |
| Web UI / dashboard | Local chat interface sufficient for v1 |
| Social sharing | Anti-feature per research — harms core value |
| Aggressive auto-tagging | Preference for explicit categorization over inference |
| Video processing (live streams) | Cannot process until stream ends |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INTAKE-01 through INTAKE-05 | Phase 1 | Pending |
| STORAGE-01 through STORAGE-05 | Phase 1 | Pending |
| SUMMARY-01 through SUMMARY-05 | Phase 1 | Pending |
| PREF-01 through PREF-04 | Phase 2 | Pending |
| SURFACE-01 through SURFACE-03 | Phase 2 | Complete (02-02) |
| CONFLICT-01 through CONFLICT-03 | Phase 3 | Complete (03-01) |
| GAP-01 through GAP-03 | Phase 3 | Complete (03-02) |
| RESEARCH-01 through RESEARCH-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-27 after 02-02 complete*
