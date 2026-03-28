# Phase 07 Research — notebook-lm-pi Integration

## What This Is
notebook-lm-pi is an unofficial Python API for Google's Notebook LM (GitHub: notebook-lm-pi by Tang Ling). It lets Claude Code talk to Notebook LM directly from terminal.

## Key Capabilities
1. **Source Sync**: Upload sources (YouTube URLs, articles, PDFs) to Notebook LM
2. **RAG Query**: Query Notebook LM's AI analysis of your sources
3. **Deliverables**: Generate infographics, slide decks, podcasts, audio overviews, mind maps, flashcards

## Why It Matters
- Free AI processing — Google pays for Notebook LM tokens
- Replaces a RAG stack that would cost $100-500/month
- Delivers outputs: podcasts, infographics, slides — things humans actually consume

## How It Works
1. User authenticates once with Google account (browser-based)
2. notebook-lm-pi stores auth tokens
3. Claude Code calls Python API → Notebook LM processes sources
4. Results returned as files/URLs

## Implementation
1. Install `notebook-lm-pi` package
2. Create `src/agent/handlers/notebook_lm_handler.py`
3. Create `notebook_lm` CLI wrapper for auth check / source upload / query
4. Integrate into research pipeline: after Tavily results, offer "Generate podcast" / "Generate infographic"
5. Deliverable URLs returned to user

## Deferred (needs API key/auth)
- Google login — requires browser auth once on Legion
- Notebook LM API calls — unofficial, could break

## Key Methods
- `upload_source(url)` — upload YouTube/URL to Notebook LM
- `query_notebook(question)` — ask question about uploaded sources
- `generate_deliverable(deliverable_type)` — create infographic/slides/podcast

## Files to Create
- `src/agent/handlers/notebook_lm_handler.py`
- `src/agent/deliverables.py`
