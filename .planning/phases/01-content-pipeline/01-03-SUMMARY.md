---
phase: 01-content-pipeline
plan: "03"
subsystem: summary
tags: [questionary, cli, summary, menu, quick-summary]
dependency_graph:
  requires:
    - phase: 01-content-pipeline-01
      provides: SQLite storage, Database.get_content()
    - phase: 01-content-pipeline-02
      provides: intake handlers, process_content()
  provides:
    - SUMMARY-01
    - SUMMARY-02
    - SUMMARY-03
    - SUMMARY-04
    - SUMMARY-05
  affects:
    - 02-memory-surfacing (preference tracking hooks)
    - agent loop integration
tech_stack:
  added:
    - questionary==2.1.1 (async CLI menus)
  patterns:
    - questionary.select().ask_async() for non-blocking CLI menus
    - Sentence extraction via regex split on [.!?]
    - Keyword-based content search for Q&A
key_files:
  created:
    - src/agent/handlers/summary_handler.py
    - tests/test_summary_flow.py
  modified:
    - requirements.txt
decisions:
  - "Used questionary.select().ask_async() for non-blocking async CLI interaction"
  - "Sentence splitting via regex r'(?<=[.!?])\s+|\n+' preserves natural pauses"
  - "Question keywords extracted via \b[a-zA-Z]{4,}\b for content matching"
patterns-established:
  - "Async CLI menus via questionary.ask_async() pattern"
  - "Content extraction functions return structured strings, not print"
requirements-completed:
  - SUMMARY-01
  - SUMMARY-02
  - SUMMARY-03
  - SUMMARY-04
  - SUMMARY-05
metrics:
  duration_minutes: 3
  completed_date: "2026-03-27"
  tasks_completed: 1
  tests_passed: 8
  commits: 2
---

# Phase 1 Plan 3: Summary Flow Summary

**4-option quick-select menu via questionary with Quick Summary (3-5 bullets), Full Breakdown (structured notes), Ask a Question (keyword search), and Save for Later (defer confirmation).**

## Performance

- **Duration:** 3 min
- **Tasks:** 1
- **Files modified:** 3
- **Tests passed:** 8 (43 total)

## Accomplishments

- Built summary_handler.py with all 4 summary modes wired to questionary async menu
- Quick Summary extracts 3-5 meaningful sentences from raw_content as markdown bullets
- Full Breakdown returns structured markdown with Key Moments, Key Quotes, and Follow-up Questions sections
- Ask a Question mode uses keyword extraction and case-insensitive search to find relevant sentences
- Save for Later returns a confirmation message with retrieval instructions

## Task Commits

1. **Task 1: Summary handler with 4-option menu** - `8d75425` (feat)
2. **Requirements update** - `c05d260` (docs)

## Files Created/Modified

- `src/agent/handlers/summary_handler.py` - show_summary_menu, quick_summary, full_breakdown, ask_question_mode, save_for_later
- `tests/test_summary_flow.py` - 8 tests covering all summary modes
- `requirements.txt` - added questionary==2.1.1

## Decisions Made

- Used questionary.select().ask_async() for non-blocking async CLI interaction
- Sentence splitting via regex preserves natural pauses in content
- Ask a Question uses 4+ character word extraction as keywords for matching

## Deviations from Plan

None - plan executed exactly as written.

## Test Fixes During Execution

**1. [Rule 3 - Blocking] questionary import and async mocking in tests**
- **Found during:** Writing tests/test_summary_flow.py
- **Issue:** questionary.select() instantiates a Win32 console UI at construction time, failing in headless test environment. Also, mock_ask_async needed proper self binding.
- **Fix:** Created MockSelector class with proper async method binding and patched at module level via monkeypatch
- **Files modified:** tests/test_summary_flow.py
- **Verification:** 8/8 tests pass
- **Committed in:** 8d75425

## Success Criteria Met

- SUMMARY-01: 4-option quick-select menu via questionary.select().ask_async()
- SUMMARY-02: Quick Summary returns 3-5 markdown bullets extracted from raw_content
- SUMMARY-03: Full Breakdown returns Key Moments, Key Quotes, Follow-up Questions sections
- SUMMARY-04: Ask a Question mode extracts keywords, searches content, returns relevant sentences
- SUMMARY-05: Save for Later returns confirmation with title and retrieval instructions

## Self-Check: PASSED

All files exist, commits verified, 43 tests pass.

---
*Phase: 01-content-pipeline*
*Plan: 01-03*
*Completed: 2026-03-27*
