# Milestones

## v1.0 — Core Research Agent Foundation
**Completed:** 2026-03-27

### What Shipped
- Content Pipeline: multi-format intake (YouTube, articles, PDFs, raw text), SQLite + markdown sync, deduplication
- Memory & Surfacing: explicit preference tracking, surfacing with topic scoring, rejected approach warnings
- Intelligence Layer: conflict detection (embeddings + cosine sim 0.85), gap detection (3+ content, 24h idle)
- Research on Demand: Tavily API integration, targeting questions, cited results

### Stats
- 8 plans executed
- 88 tests passing
- 4 phases, 100% complete

## v2.0 — Research Stack Upgrade
**Completed:** 2026-03-27

### What Shipped
- Phase 05: yt-dlp YouTube search skill — zero-cost YouTube metadata discovery
- Phase 06: Obsidian vault integration — visual knowledge graph with [[links]], backlinks, daily session notes
- Phase 07: notebook-lm-pi integration — stub handler ready for API key (deferred auth)
- Phase 08: Research session logging — tracks all research sessions in SQLite
- Phase 09: Self-improving CLAUDE.md — project conventions + session pattern tracking

### Stats
- 5 phases executed
- 141 tests passing (+53 from v1.0)
- 5 phases, 100% complete
- yt-dlp search (zero-cost), Obsidian vault (visual graph), session history

### Deferred (needs API keys)
- notebook-lm-pi full integration (needs Google auth + NOTEBOOK_LM_API_KEY)
- Tavily API key already present

---
*Last updated: 2026-03-27 after v2.0 complete*
