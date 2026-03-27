# Research Analyst Agent

## What This Is

A persistent research analyst agent that runs 24/7 on Legion. You throw any content at it — videos, articles, papers, books, reels, raw text — and it extracts, stores, summarizes, and learns from everything. It remembers what you've liked and rejected, surfaces relevant knowledge in conversations, warns you when you're about to repeat a rejected approach, and compares conflicting sources when you ask.

Core value: A persistent research memory that learns what you like/dislike and surfaces the right knowledge at the right time.

## Core Value

You stop re-watching videos to find one thing you vaguely remember. Everything you've ever sent it is searchable, comparable, and alive in your conversations.

## Requirements

### Active

- [ ] Agent runs persistently on Legion, loads on startup
- [ ] Content intake: paste links (YouTube, articles, PDFs) or raw text — auto-detects type
- [ ] Extracts content using video-to-knowledge, article scrapers, PDF parsers
- [ ] Stores in SQLite database + human-readable markdown files (synced)
- [ ] After intake: quick-select menu (summary / full breakdown / ask question / save for later)
- [ ] Topic categorization by content topic, not media type
- [ ] Preference tracking: stores positive/negative reactions, comparison choices, rejections with reasons
- [ ] Content surfacing: when you ask about something, agent pulls from knowledge base
- [ ] Rejected approach warnings: if you mention/use something you rejected before, agent warns you
- [ ] Conflict detection: when overlapping content detected, compare approaches and ask which you prefer
- [ ] Gap detection: if 3+ pieces on same topic with no new content after 24h, ask if you want to explore
- [ ] Research on demand: user asks "find me more like this" → agent asks targeting questions → then searches

### Out of Scope

- Discord/Dispatch integration — manual intake only for now
- Proactive research (goes out and finds things unprompted) — wait until core is solid
- Multi-user support — single user v1
- Health monitoring dashboard — you'll notice if Legion is down
- Cloudflare tunnel / remote access — local only for now

## Context

- Runs on Legion (Windows, 24/7)
- Uses existing MCP tools internally: video-to-knowledge, exa-search, deep-research
- Storage: SQLite (fast queries) + markdown files (human-readable)
- No communication layer yet — tested by pasting content directly in chat

## Constraints

- **Storage**: SQLite + markdown files, kept in sync — no external DB
- **Communication**: Local only, no remote access — Discord/Dispatch deferred
- **Research**: Reactive only, never proactive without user direction

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Legion as host | Always-on, right place for persistent agent | — Pending |
| SQLite + markdown | Fast queries + human-readable backup | — Pending |
| No proactive research v1 | Core storage/surfacing first, intelligence later | — Pending |
| Explicit preference signals | Don't infer, ask "should I remember that?" | — Pending |
| Gap detection: 3+ pieces + 24h idle | Don't interrupt while user is still collecting | — Pending |

---
*Last updated: 2026-03-26 after initial definition*
