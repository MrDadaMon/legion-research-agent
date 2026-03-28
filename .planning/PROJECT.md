# Research Analyst Agent

## What This Is

A persistent research analyst agent that runs 24/7 on Legion. You throw any content at it — videos, articles, papers, books, reels, raw text — and it extracts, stores, summarizes, and learns from everything. It remembers what you've liked and rejected, surfaces relevant knowledge in conversations, warns you when you're about to repeat a rejected approach, and compares conflicting sources when you ask. In v2.0, it becomes a full research workstation with visual knowledge graphs, free AI processing, and self-improving patterns.

Core value: A persistent research memory that learns what you like/dislike and surfaces the right knowledge at the right time.

## Core Value

You stop re-watching videos to find one thing you vaguely remember. Everything you've ever sent it is searchable, comparable, and alive in your conversations.

## Current Milestone: v2.0 Research Stack Upgrade

**Goal:** Transform Legion from a research database into a full research workstation matching the Chase workflow — Obsidian vault for visual knowledge graphs, notebook-lm-pi for free AI processing, yt-dlp for YouTube sourcing, deliverable generation, and a self-improving agent loop.

**Target features:**
- Obsidian vault integration (markdown vault becomes visual knowledge graph)
- notebook-lm-pi integration (free AI RAG + deliverable generation)
- yt-dlp YouTube search skill (zero-cost content discovery)
- Research deliverable outputs (infographics, slide decks, podcasts)
- Self-improving CLAUDE.md: agent updates conventions based on interaction patterns

## Requirements

### Validated (v1.0 — shipped)

- ✓ Content intake: paste links (YouTube, articles, PDFs) or raw text — auto-detects type — Phase 1
- ✓ SQLite + markdown sync with deduplication — Phase 1
- ✓ Quick-select menu after intake — Phase 1
- ✓ Preference tracking with explicit confirmation — Phase 2
- ✓ Content surfacing with topic scoring — Phase 2
- ✓ Conflict detection with embeddings (cosine sim 0.85) — Phase 3
- ✓ Gap detection (3+ content, 24h idle) — Phase 3
- ✓ Research on demand with targeting questions + cited results via Tavily — Phase 4

### Active (v2.0)

- [x] Obsidian vault as primary knowledge graph (replaces plain content/ folder) — Phase 06
- [x] notebook-lm-pi stub handler (API key deferred to Legion setup) — Phase 07
- [x] yt-dlp YouTube search skill for zero-cost content discovery — Phase 05
- [x] Deliverable generation stubs (infographics, slide decks, podcasts) — Phase 07
- [x] Self-improving CLAUDE.md: project conventions + session patterns — Phase 09
- [x] Research session logging (track what was researched over time) — Phase 08

### Out of Scope

- Discord/Dispatch integration — manual intake only for now
- Proactive research (goes out and finds things unprompted) — wait until core is solid
- Multi-user support — single user v1
- Health monitoring dashboard — you'll notice if Legion is down
- Cloudflare tunnel / remote access — local only for now
- Full GraphRAG (Obsidian gives 80% of relationship mapping without the complexity)

## Context

- Runs on Legion (Windows, 24/7)
- Uses existing MCP tools internally: video-to-knowledge, exa-search, deep-research
- v1.0 storage: SQLite (fast queries) + markdown files (human-readable)
- v2.0 storage: Same SQLite + Obsidian vault (visual layer on top)
- No communication layer yet — tested by pasting content directly in chat
- Reference workflow: Chase's Claude Code + Obsidian + Notebook LM + Skill Creator stack

## Constraints

- **Storage**: SQLite + markdown files (v1.0), Obsidian vault (v2.0) — keep SQLite as source of truth
- **Communication**: Local only, no remote access — Discord/Dispatch deferred
- **Research**: Reactive only, never proactive without user direction
- **Vendor**: notebook-lm-pi is unofficial API — keep Tavily as backup for research
- **Legion compatibility**: notebook-lm-pi requires Google auth — needs browser login once

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Legion as host | Always-on, right place for persistent agent | ✓ Confirmed v1.0 |
| SQLite + markdown | Fast queries + human-readable backup | ✓ Confirmed v1.0 |
| Explicit preference signals | Don't infer, ask "should I remember that?" | ✓ Confirmed v1.0 |
| Gap detection: 3+ pieces + 24h idle | Don't interrupt while user is still collecting | ✓ Confirmed v1.0 |
| Cosine similarity 0.85 threshold | Balance between precision and recall for conflict detection | ✓ Confirmed v1.0 |
| Tavily for research | Web search with citations — primary research method | ✓ Confirmed v1.0 |
| Obsidian vault (v2.0) | Visual knowledge graph + linked notes — replaces plain content/ folder | — New |
| notebook-lm-pi (v2.0) | Free AI RAG + deliverables — offloads token cost to Google | — New |
| yt-dlp (v2.0) | Zero-cost YouTube metadata scraping — complements Tavily | — New |
| CLAUDE.md self-improvement (v2.0) | Agent updates conventions from interaction patterns | — New |

---
*Last updated: 2026-03-27 after v1.0 complete, v2.0 milestone started*
