# Legion Research Agent — Project Conventions

## Project Identity

A persistent research analyst agent that runs 24/7 on Legion. You throw any content at it — videos, articles, papers, books, reels, raw text — and it extracts, stores, summarizes, and learns from everything.

## Obsidian Vault Conventions

When writing notes to the Obsidian vault, follow these conventions:

### Linking
- **Topic links**: `[[topic-slug-id|Display Title]]` — links to related content
- **Embeds**: `![[note-slug-id]]` — embeds content of another note
- **Backlinks**: Every note tracks what links TO it via the backlinks index

### YAML Frontmatter
Every note must have this frontmatter:
```yaml
---
id: 123
title: Note Title
source_type: youtube|article|pdf|text
source_url: https://...
topic: topic-slug
processed_date: YYYY-MM-DD
content_hash: sha256-hash
tags: [tag1, tag2]
related:
  - id: 456
    title: Related Note
    link: [[related-note-slug-456|Related Note]]
---
```

### Daily Session Notes
Research sessions are logged in `sessions/YYYY-MM-DD.md`:
```markdown
---
date: 2026-03-27
---

# Research Session: 2026-03-27

**Research Query:** trading bot strategies

**Summary:** Found 3 good videos on mean-reversion trading

### Content Consumed
- [[video-123|Trading Bot Video 1]]
- [[article-456|Crypto Trading Article]]

### Notes
<!-- Session notes go here -->
```

---

## Research Patterns

### What Works
- yt-dlp search for YouTube-specific content discovery (zero cost)
- Tavily for general web research with citations
- notebook-lm-pi for AI-generated deliverables (podcasts, infographics)
- Session logging to track research history over time

### What Doesn't Work

### Query Formulation Tips
- Be specific: "trading bots mean reversion" beats "trading"
- Mention content type: "YouTube videos on X" triggers yt-dlp search
- "Find me more like this on X" uses stored content as seed

### Preferred Content Types
- YouTube videos for visual/technical explanations
- Articles for news and updates
- PDFs for deep-dive research papers

---

## Session Notes

<!-- Agent appends patterns here after each research session -->
