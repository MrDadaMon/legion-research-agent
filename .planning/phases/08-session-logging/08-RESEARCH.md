# Phase 08 Research — Research Session Logging

## What This Is
Track what you've researched over time. Each research session appended to a log so you can see your research history. Append-only log of sessions with timestamps, queries, and results.

## What to Track
Each research session:
- `session_id` (auto-increment)
- `timestamp` (datetime)
- `query` (what you asked)
- `seed_content_id` (which stored content triggered the research, if any)
- `results_count` (how many results returned)
- `deliverables_requested` (what deliverables were generated, if any)
- `notes` (optional user notes)

## Why This Matters
- You can look back: "what did I research last week?"
- Identifies research patterns / gaps
- Feeds into gap detection (if you researched X 3x but still don't have answers)
- Enables session-based summaries

## Database Schema
```sql
CREATE TABLE research_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    query TEXT NOT NULL,
    seed_content_id INTEGER REFERENCES content(id) ON DELETE SET NULL,
    results_count INTEGER DEFAULT 0,
    deliverable_types TEXT,  -- comma-separated: "podcast,infographic"
    notes TEXT
);
```

## Implementation
1. Add `research_sessions` table to Database class
2. Log session start before research
3. Log session end after results returned
4. Add `get_recent_sessions(limit=10)` method
5. Add `get_session_history(topic_filter)` method
6. Surface session history when user asks "what have I researched?"

## Files to Modify
- `src/storage/database.py` (add table + methods)
- `src/agent/handlers/research_handler.py` (log sessions)
- `src/agent/research_utils.py` (add session display)
