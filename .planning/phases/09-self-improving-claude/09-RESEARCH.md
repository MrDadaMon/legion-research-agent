# Phase 09 Research — Self-Improving CLAUDE.md

## What This Is
After each research session, agent updates CLAUDE.md based on what worked. The CLAUDE.md becomes a "living brain within the brain" — distilled preferences and conventions that improve over time.

## What to Track in CLAUDE.md
From the Chase workflow video:
- Successful research patterns (what queries worked well)
- Content types that performed well (YouTube vs article vs PDF)
- Preferred deliverable formats
- Obsidian linking conventions that emerged
- Research session patterns

## How It Works
After each research session (Phase 08):
1. Agent reviews what happened: query → results → what user picked
2. Agent asks: "Did this research session go well? Any patterns to note?"
3. Agent updates `CLAUDE.md` with new insights under `# Research Patterns` section
4. Future sessions consult this section for better query formulation

## CLAUDE.md Structure (new sections)
```markdown
# Research Patterns

## What Works
- Query formulation: ...
- Preferred sources: ...
- Deliverable types: ...

## What Doesn't Work
- Failed patterns: ...
- Topics to avoid: ...

## Session Notes
- [2026-03-27]: ...
```

## Implementation
1. Create `CLAUDE.md` in project root (doesn't exist yet)
2. Add `update_claude_md(session_review)` function
3. After research session completes, call update function
4. Pattern analyzer reads CLAUDE.md before formulating queries

## Files to Create/Modify
- `CLAUDE.md` (new — project-level conventions)
- `src/agent/research_utils.py` (add pattern review after session)
- No new handlers needed

## Deferred
- Automated CLAUDE.md updates without prompting — requires more sophistication
- Pattern extraction from session history — manual review is safer
