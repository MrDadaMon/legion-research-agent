# Roadmap: Legion Research Agent

## Overview

A persistent research analyst that runs 24/7 on Legion, learning from everything you throw at it — videos, articles, PDFs, raw text. It extracts, stores, summarizes, tracks preferences, surfaces relevant knowledge, detects conflicts, and fills gaps. The journey goes from cold start (agent loop, one format) to intelligent research partner (conflict resolution, gap detection, targeted research).

## Phases

- [ ] **Phase 1: Content Pipeline** - Agent foundation: intake, extraction, SQLite storage, markdown sync, summary flow
- [ ] **Phase 2: Memory & Surfacing** - Preference tracking, rejection warnings, proactive surfacing, topic management
- [ ] **Phase 3: Intelligence Layer** - Conflict detection with resolution flow, gap detection with research suggestions
- [ ] **Phase 4: Research on Demand** - Targeted research with clarification questions, cited results

## Phase Details

### Phase 1: Content Pipeline
**Goal**: User can add content in any format and get structured summaries
**Depends on**: Nothing (first phase)
**Requirements**: INTAKE-01, INTAKE-02, INTAKE-03, INTAKE-04, INTAKE-05, STORAGE-01, STORAGE-02, STORAGE-03, STORAGE-04, STORAGE-05, SUMMARY-01, SUMMARY-02, SUMMARY-03, SUMMARY-04, SUMMARY-05
**Success Criteria** (what must be TRUE):
  1. User pastes a YouTube URL and receives a transcript within seconds
  2. User pastes an article URL and receives scraped main content
  3. User pastes raw text and it is classified and stored correctly
  4. User attaches PDF content and receives extracted text
  5. Content is stored in SQLite with all required fields (id, source_type, source_url, title, raw_content, processed_date, content_hash)
  6. Duplicate content is detected via content_hash and reference_count incremented
  7. Human-readable markdown file exists for each content item, organized by topic
  8. SQLite and markdown stay in sync (SQLite is source of truth)
  9. After any content is processed, a 4-option quick-select menu appears (Quick Summary / Full Breakdown / Ask a Question / Save for Later)
  10. Quick Summary returns 3-5 key points in bullet format
**Plans**: 3 plans

Plans:
- [x] 01-01: Storage foundation - SQLite WAL mode, markdown sync, deduplication (wave 1)
- [x] 01-02: Asyncio agent core with intake handlers (wave 2)
- [x] 01-03: Summary flow with quick-select menu (wave 3)

### Phase 2: Memory & Surfacing
**Goal**: Agent remembers preferences and proactively surfaces relevant knowledge
**Depends on**: Phase 1
**Requirements**: PREF-01, PREF-02, PREF-03, PREF-04, SURFACE-01, SURFACE-02, SURFACE-03
**Success Criteria** (what must be TRUE):
  1. After a comparison, agent asks "Should I remember that you prefer X over Y?" before updating the profile
  2. When user mentions or uses a rejected approach, agent warns with the stored reason
  3. User can ask "what do I have on X?" and agent returns relevant content with sources
  4. Agent surfaces relevant knowledge during conversations when context matches
  5. Each surfaced item includes source URL, date, and brief description
**Plans**: 2 plans

Plans:
- [ ] 02-01: Preference tracking with confirmation loop, rejection storage, warning system
- [ ] 02-02: Content surfacing with topic queries and proactive knowledge delivery

### Phase 3: Intelligence Layer
**Goal**: Agent detects conflicts and gaps in user's knowledge base
**Depends on**: Phase 2
**Requirements**: CONFLICT-01, CONFLICT-02, CONFLICT-03, GAP-01, GAP-02, GAP-03
**Success Criteria** (what must be TRUE):
  1. When new content overlaps with existing content on the same topic, agent flags the conflict
  2. Agent presents key points of disagreement between conflicting sources
  3. User can resolve a conflict by choosing preferred approach, updating their preference profile
  4. After 3+ content pieces on a topic with 24h+ idle time, agent suggests gap exploration
  5. Agent asks targeting questions before initiating gap research
  6. Agent presents gap research results with clear accept/reject decision per item
**Plans**: 2 plans

Plans:
- [ ] 03-01: Conflict detection with overlap flagging, disagreement presentation, resolution flow
- [ ] 03-02: Gap detection with idle monitoring, targeting questions, research presentation

### Phase 4: Research on Demand
**Goal**: User can request targeted research on any stored topic
**Depends on**: Phase 3
**Requirements**: RESEARCH-01, RESEARCH-02, RESEARCH-03
**Success Criteria** (what must be TRUE):
  1. User can say "find me more like this" on any stored content
  2. Agent asks 1-2 targeting questions before searching
  3. Results returned include citations, source URLs, and relevance explanation
**Plans**: 1 plan

Plans:
- [ ] 04-01: Research on demand with targeting questions and cited results

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Content Pipeline | 0/3 | Not started | - |
| 2. Memory & Surfacing | 0/2 | Not started | - |
| 3. Intelligence Layer | 0/2 | Not started | - |
| 4. Research on Demand | 0/1 | Not started | - |

## Coverage

**v1 Requirements Mapping:**
- INTAKE-01, INTAKE-02, INTAKE-03, INTAKE-04, INTAKE-05 -> Phase 1
- STORAGE-01, STORAGE-02, STORAGE-03, STORAGE-04, STORAGE-05 -> Phase 1
- SUMMARY-01, SUMMARY-02, SUMMARY-03, SUMMARY-04, SUMMARY-05 -> Phase 1
- PREF-01, PREF-02, PREF-03, PREF-04 -> Phase 2
- SURFACE-01, SURFACE-02, SURFACE-03 -> Phase 2
- CONFLICT-01, CONFLICT-02, CONFLICT-03 -> Phase 3
- GAP-01, GAP-02, GAP-03 -> Phase 3
- RESEARCH-01, RESEARCH-02, RESEARCH-03 -> Phase 4

**Coverage:** 22/22 requirements mapped
