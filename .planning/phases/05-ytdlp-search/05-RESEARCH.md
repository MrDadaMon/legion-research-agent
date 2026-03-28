# Phase 05 Research — yt-dlp YouTube Search

## What This Is
yt-dlp YouTube search skill — zero-cost content discovery using yt-dlp (already installed) to scrape YouTube metadata (title, views, channel, duration, URL). Complements Tavily web search with YouTube-specific discovery.

## Approach
1. Use `yt-dlp --dump-json` to get video metadata without downloading
2. Parse JSON output for: title, uploader, view_count, duration, upload_date, webpage_url
3. Search via keyword query using yt-dlp's search capabilities
4. Return ranked list of results with metadata for user selection
5. Selected videos can be fed directly to intake pipeline (YouTube URL)

## Why This Matters
- Zero-cost content discovery (Tavily costs money per search)
- YouTube-specific content (better than general web for video-based research)
- yt-dlp already installed — no new dependencies
- Metadata-only (no transcript download = fast)

## Implementation Notes
- Use `subprocess.run` to call yt-dlp since it's a CLI tool
- Parse JSON output for structured metadata
- No API key needed
- Rate limiting: be respectful, add delays between searches

## Files to Create/Modify
- `src/agent/handlers/ytdlp_search_handler.py` (new)
- `src/agent/research_utils.py` (extend for yt-dlp search)
- `requirements.txt` (add yt-dlp)

## Out of Scope
- Transcript extraction (use existing youtube_transcript_api)
- Video downloading (metadata only)
- Channel analytics
