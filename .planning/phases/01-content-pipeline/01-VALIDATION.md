---
phase: 01
slug: content-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 0.26.0 |
| **Config file** | pytest.ini or pyproject.toml (Wave 0 creates) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ --tb=short` |
| **Estimated runtime** | ~30-60 seconds (Phase 1, 4 content types) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01-01 | 1 | STORAGE-01 | unit | `pytest tests/test_storage/test_database.py -x` | W0 | pending |
| 01-01-02 | 01-01 | 1 | STORAGE-02, STORAGE-05 | unit | `pytest tests/test_storage/test_database.py -x` | W0 | pending |
| 01-01-03 | 01-01 | 1 | STORAGE-03, STORAGE-04 | integration | `pytest tests/test_storage/test_sync_manager.py -x` | W0 | pending |
| 01-02-01 | 01-02 | 2 | INTAKE-05 | unit | `pytest tests/test_content_detector.py -x` | W0 | pending |
| 01-02-02 | 01-02 | 2 | INTAKE-03 | unit | `pytest tests/test_extractors/test_text_classifier.py -x` | W0 | pending |
| 01-02-03 | 01-02 | 2 | INTAKE-01, INTAKE-02, INTAKE-04 | unit | `pytest tests/test_extractors/ -x` | W0 | pending |
| 01-03-01 | 01-03 | 3 | SUMMARY-01, SUMMARY-02, SUMMARY-03, SUMMARY-04, SUMMARY-05 | integration | `pytest tests/test_summary_flow.py -x` | W0 | pending |

*Status: pending = not run | green = passed | red = failed | flaky = intermittent*

---

## Wave 0 Requirements

All test files must be created before execution begins.

- [ ] `tests/conftest.py` — shared fixtures (db_path, sample_content, event_loop)
- [ ] `tests/test_extractors/test_youtube_extractor.py` — covers INTAKE-01
- [ ] `tests/test_extractors/test_article_scraper.py` — covers INTAKE-02
- [ ] `tests/test_extractors/test_text_classifier.py` — covers INTAKE-03
- [ ] `tests/test_extractors/test_pdf_extractor.py` — covers INTAKE-04
- [ ] `tests/test_content_detector.py` — covers INTAKE-05
- [ ] `tests/test_storage/test_database.py` — covers STORAGE-01, STORAGE-02, STORAGE-05
- [ ] `tests/test_storage/test_markdown_store.py` — covers STORAGE-03
- [ ] `tests/test_storage/test_sync_manager.py` — covers STORAGE-04
- [ ] `tests/test_summary_flow.py` — covers SUMMARY-01 through SUMMARY-05
- [ ] `pytest.ini` or update `pyproject.toml` — pytest-asyncio configuration
- [ ] Framework install: `pip install pytest-asyncio questionary`

*No existing test infrastructure — all Wave 0 files need to be created.*

---

## Manual-Only Verifications

All phase behaviors have automated verification via pytest.

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
