---
phase: 2
slug: memory-surfacing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | tests/conftest.py (existing from Phase 1) |
| **Quick run command** | `pytest tests/ -k "pref or surface" -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -k "pref or surface" -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | PREF-01 | unit | `pytest tests/ -k "test_preference_confirmation" -v` | tests/test_preferences.py (to be created) | ⬜ pending |
| 02-01-02 | 01 | 1 | PREF-02 | unit | `pytest tests/ -k "test_rejection_storage" -v` | tests/test_preferences.py (to be created) | ⬜ pending |
| 02-01-03 | 01 | 1 | PREF-03 | unit | `pytest tests/ -k "test_profile_read_write" -v` | tests/test_preferences.py (to be created) | ⬜ pending |
| 02-01-04 | 01 | 1 | PREF-04 | unit | `pytest tests/ -k "test_rejection_warning" -v` | tests/test_preferences.py (to be created) | ⬜ pending |
| 02-02-01 | 02 | 1 | SURFACE-01 | unit | `pytest tests/ -k "test_what_do_i_have" -v` | tests/test_surfacing.py (to be created) | ⬜ pending |
| 02-02-02 | 02 | 1 | SURFACE-02 | unit | `pytest tests/ -k "test_proactive_surface" -v` | tests/test_surfacing.py (to be created) | ⬜ pending |
| 02-02-03 | 02 | 1 | SURFACE-03 | unit | `pytest tests/ -k "test_surfacing_includes_metadata" -v` | tests/test_surfacing.py (to be created) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_preferences.py` — stubs for PREF-01 through PREF-04
- [ ] `tests/test_surfacing.py` — stubs for SURFACE-01 through SURFACE-03
- [ ] `tests/conftest.py` — ensure pytest-asyncio fixtures are available (existing from Phase 1)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Confirmation loop prompts user correctly | PREF-01 | CLI interaction, hard to unit test | Run agent, compare two items, verify prompt appears |
| Rejection warning displays correctly | PREF-04 | CLI interaction, requires user mention simulation | Run agent, mention rejected approach, verify warning |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
