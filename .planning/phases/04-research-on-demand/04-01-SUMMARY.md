---
phase: 04-research-on-demand
plan: 04-01
subsystem: research
tags: [tavily, research-api, citations, questionary]

# Dependency graph
requires:
  - phase: 03-intelligence-layer
    provides: gap detection with targeting questions, content storage
provides:
  - "find me more like this" research trigger detection
  - Tavily API integration for cited web research
  - Shared targeting question utilities between gap_handler and research_handler
  - Citation formatting with title, URL, relevance, and key findings
affects: [surfacing-handler, gap-handler, research-workflow]

# Tech tracking
tech-stack:
  added: [tavily-python==0.5.0]
  patterns: [shared utilities pattern, API response formatting, trigger detection via regex]

key-files:
  created:
    - src/agent/research_utils.py
    - src/agent/handlers/research_handler.py
    - .env.example
  modified:
    - src/agent/handlers/gap_handler.py
    - requirements.txt

key-decisions:
  - "Use TavilyClient.research() for comprehensive cited results (not just search)"
  - "Generalize ask_targeting_questions into ask_research_targeting_questions for code reuse"
  - "Research handler accepts ContentItem dicts (not objects) for cross-handler compatibility"

patterns-established:
  - "Pattern: Shared utility functions in research_utils.py for targeting questions"
  - "Pattern: Citation format includes title, source URL, relevance count, and key finding excerpt"

requirements-completed: [RESEARCH-01, RESEARCH-02, RESEARCH-03]

# Metrics
duration: 4min
completed: 2026-03-27
---

# Phase 04 Plan 01: Research on Demand Summary

**Research-on-demand with Tavily API integration for "find me more like this" functionality**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T07:26:31Z
- **Completed:** 2026-03-27T07:30:26Z
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments

- Created research_handler.py with Tavily API integration for "find me more like this" research
- Created shared research_utils.py with generalized targeting question logic
- Updated gap_handler.py to use shared ask_research_targeting_questions (eliminated code duplication)
- Added tavily-python dependency and .env.example with TAVILY_API_KEY template

## Task Commits

Each task was committed atomically:

1. **Task 1: Create research_utils.py with shared targeting question logic** - `df18851` (feat)
2. **Task 2: Create research_handler.py with Tavily integration** - `7a3d460` (feat)
3. **Task 3: Update gap_handler to use shared research_utils** - `60f374a` (refactor)
4. **Task 4: Add tavily-python and .env.example** - `14c2e56` (chore)

**Plan metadata:** `14c2e56` (docs: complete plan)

## Files Created/Modified

- `src/agent/research_utils.py` - Shared targeting question logic (ask_research_targeting_questions, build_research_query, format_cited_results)
- `src/agent/handlers/research_handler.py` - Research-on-demand with Tavily API (is_research_query, extract_content_reference, execute_research, handle_research_request)
- `src/agent/handlers/gap_handler.py` - Refactored to use shared ask_research_targeting_questions
- `requirements.txt` - Added tavily-python==0.5.0
- `.env.example` - Added TAVILY_API_KEY template

## Decisions Made

- Used TavilyClient.research() endpoint (not search) for comprehensive results with built-in citations
- Generalized gap_handler's ask_targeting_questions into ask_research_targeting_questions for reuse
- research_handler converts ContentItem objects to dicts for research_utils compatibility
- Citation format: title, source URL, relevance explanation, and key finding excerpt per result

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

**External services require manual configuration.** See [.env.example](./.env.example) for:
- `TAVILY_API_KEY` - Get from tavily.com and add to your .env file

## Next Phase Readiness

- Research-on-demand infrastructure complete
- gap_handler successfully uses shared targeting questions
- Ready for integration with main agent loop (surfacing_handler can detect research queries)

---
*Phase: 04-research-on-demand*
*Completed: 2026-03-27*
