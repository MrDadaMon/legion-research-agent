# Phase 05 Verification — yt-dlp YouTube Search

## Status: Complete

## What Was Built

### Handler
- `src/agent/handlers/ytdlp_search_handler.py` — ~300 lines
  - `search_youtube(query, max_results, months)` — calls `yt-dlp --dump-json --search` with anti-bot measures
  - `get_video_metadata(url)` — gets metadata for a single video with random delay
  - `is_youtube_search_query()` — detection with 7 trigger patterns
  - `extract_youtube_search_topic()` — extracts search topic from query
  - `format_youtube_results()` — formats results with quality signal
  - `YouTubeVideo` NamedTuple with: title, url, uploader, view_count, subscriber_count, duration, upload_date, views_per_sub

### Anti-Bot Measures
- **User-Agent rotation**: 6 realistic browser strings (Chrome, Firefox, Safari) randomly selected
- **Rate limiting**: 10s minimum between searches, enforced globally
- **Random jitter**: `delay + random(0, delay)` between every request
- **Result shuffling**: top third keeps order, rest shuffled — relevant but non-bot
- **Metadata delay**: 3s pause before fetching individual video metadata

### Trigger Patterns (auto-detected)
- "find videos on X" / "find video on X"
- "search YouTube for X"
- "what's on YouTube about X" / "what is on youtube about X"
- "recommend me some videos on X"
- "youtube search for X"
- "look up videos on X"

### Quality Signal
- **Views/subs ratio**: `view_count / subscriber_count` — high ratio = genuinely good video regardless of channel size
- **6-month default filter**: recent content first, matches how humans naturally search
- Results displayed ranked by quality signal

### Tests
- `tests/test_ytdlp_search.py` — 22 tests, all passing

## Success Criteria: Met
- [x] yt-dlp search returns ranked YouTube results with metadata
- [x] Auto-detected when user says "find videos on X" or similar
- [x] Selected videos can be added to knowledge base via intake pipeline
- [x] No API key required
- [x] Anti-bot measures prevent detection
- [x] 22 tests passing

## Out of Scope (Deferred)
- Transcript extraction (existing youtube_transcript_api handles this)
- Video downloading (metadata only)
