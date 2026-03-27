# Handoff — Legion Research Agent v2.0 Milestone

## Where We Are

**Project:** Legion Research Agent — a persistent 24/7 research analyst running on Legion (your Ubuntu server at 192.168.12.243)

**Status:** Just completed v1.0 milestone (4 phases, 8/8 plans, 88 tests passing). Just started v2.0 milestone — committed the milestone start to git. About to define requirements for v2.0 when you get back.

**What was happening right before you left:**
- You shared 3 YouTube videos from Chase (Floflo) about combining Claude Code + Obsidian + Notebook LM + Skill Creator into a unified research workflow
- We watched all 3 transcripts (downloaded via yt-dlp)
- You said yes to implementing everything: Obsidian vault, notebook-lm-pi, yt-dlp YouTube search, deliverables, and all the improvements
- I started the v2.0 milestone: updated PROJECT.md, STATE.md, MILESTONES.md, committed everything
- I was about to skip research and go straight to defining requirements for the new milestone

**What you asked me to do:**
- `/clear` to get fresh context
- Come back and say something that makes me "pick up exactly where we left off"
- The key phrase is: **"continue v2.0"** — this signals you want me to resume the milestone workflow

---

## What You Told Me to Build (v2.0)

You were 100% clear on what you want from those 3 videos:

### Add Everything (new capabilities):
1. **Obsidian vault** — Replace the plain `content/` folder with an Obsidian vault. Obsidian gives you a visual graph of how all your notes connect. The vault lives on your local machine and Claude Code writes properly linked markdown files to it.

2. **notebook-lm-pi** — Unofficial Python API for Notebook LM (GitHub: notebook-lm-pi by Tang Ling). Lets Claude Code talk to Notebook LM directly from terminal. Notebook LM does free AI RAG processing — you pay zero tokens for analysis. Also gives deliverables: infographics, slide decks, podcasts, audio overviews, mind maps, flashcards.

3. **yt-dlp YouTube search skill** — Claude Code uses yt-dlp (already installed) to scrape YouTube metadata: titles, views, channel, duration, URL. Zero-cost content discovery. Replace or complement Tavily web search with YouTube-specific search.

4. **Deliverable generation** — From research results, generate: infographics, slide decks, podcasts, audio overviews, mind maps, flashcards. This comes through notebook-lm-pi, not Tavily.

5. **Research session logging** — Track what you've researched over time. Each research session appended to a log so you can see your research history.

### Improve (existing v1.0 capabilities):
1. **Research results format** — Add optional infographic/slide deck generation alongside the text results
2. **CLAUDE.md with Obsidian conventions** — Add `[[double bracket links]]`, `![[embeds]]`, `![[backlinks]]` so Claude Code writes properly Obsidian-formatted notes
3. **Self-improving agent loop** — After each research session, ask Claude to update CLAUDE.md based on what worked

### Keep (v1.0 — do NOT remove):
- SQLite + sqlite-vec for embeddings (keeps everything local, no external DB)
- Tavily for web research (notebook-lm-pi complements it, doesn't replace it)
- All Phase 1-4 code: content pipeline, preference tracking, surfacing, conflict detection, gap detection, research on demand
- All 88 tests that pass

### Discard (from original analysis — you overrode me):
- **Notebook LM for RAG as competitor to SQLite** — You said keep both as layers. Notebook LM for AI processing + visualization, SQLite for your own private knowledge base.
- **Skill Creator plugin** — You correctly noted we already have GSD which serves the same purpose
- **Full GraphRAG** — Obsidian gives 80% of relationship mapping without the complexity

---

## What I Was Doing When You Left

I was in the **gsd:new-milestone** workflow for v2.0. I had just:
1. Read PROJECT.md, STATE.md
2. Created MILESTONES.md (v1.0 summary, v2.0 started)
3. Updated PROJECT.md with v2.0 Current Milestone section
4. Updated STATE.md for v2.0
5. Committed everything

Then I asked if you wanted research or to skip to requirements. You said **"go ahead and skip search"** — meaning skip formal research and go straight to requirements.

**Next step (your job when you come back):** Say **"continue v2.0"** and I'll resume — I'll define requirements for v2.0 (Obsidian vault, notebook-lm-pi, yt-dlp, deliverables, self-improvement), scope them, create the roadmap, and start executing phases.

---

## The 3 Videos (Quick Reference)

**Video 1 — Claude Code + Notebook LM (Free RAG Stack)**
- yt-dlp scrapes YouTube metadata → sends to Notebook LM via notebook-lm-pi
- Notebook LM does all AI analysis for free (Google pays)
- Returns: infographics, slide decks, podcasts, audio overviews, mind maps, flashcards
- Replaces a RAG stack that would cost hundreds/month

**Video 2 — Claude Code + Obsidian (Persistent Memory)**
- Obsidian vault = local folder with markdown files + visual knowledge graph
- Claude Code acts as author — writes all markdown with proper `[[linking]]` conventions
- `claude.md` = "living brain within the brain" — distilled preferences over time
- Obsidian is the "happy medium" between messy files and full GraphRAG

**Video 3 — Full Combined Workflow + Skill Creator**
- Skill Creator chains: YouTube search → Notebook LM → Obsidian vault → deliverable
- One prompt: "find me top 5 videos on X, analyze them, give me an infographic"
- Self-improving loop: more research = more notes = better context = better research
- Everything helps everything else

---

## Technical Notes

**notebook-lm-pi:**
- GitHub: notebook-lm-pi (Tang Ling)
- Requires Google login (browser-based auth — need to do once on Legion)
- Unofficial API — could break with Notebook LM updates
- Alternative: keep Tavily as backup for web research

**yt-dlp:**
- Already installed on the system
- Used for: video metadata (title, views, channel, duration, URL)
- Not for: transcript extraction (we use yt-dlp for metadata, video-to-knowledge for transcripts)

**Obsidian vault:**
- Local folder — lives wherever you want
- Markdown files with `[[double bracket links]]`
- Graph view shows how notes connect
- No cloud sync needed — local only

**Tavily:**
- Already integrated in `research_handler.py`
- Stays as primary web research
- notebook-lm-pi adds free AI processing layer

---

## Files Changed (committed during this session)

```
A .planning/MILESTONES.md   (v1.0 summary, v2.0 started)
M .planning/PROJECT.md     (added v2.0 Current Milestone section)
M .planning/STATE.md        (reset for v2.0)
```

---

## What to Say When You Come Back

**Say this exact phrase:** "continue v2.0"

I'll understand: resume the new-milestone workflow, skip research (you already approved), go straight to defining requirements for Obsidian vault, notebook-lm-pi, yt-dlp, deliverables, and self-improvement.

---

## Your Goals (from your perspective)

You said: **"I'm about to go to sleep so just do whatever you recommend. Don't ask me any more questions. Just run everything until it's complete. Before you start tell me exactly what you're going to do so I know if I can do just anything."**

When you wake up: **"continue v2.0"**

I'll take it from there: define requirements, create roadmap, execute phases — fully autonomous until v2.0 is complete.

---

## v1.0 Complete — What Shipped

| Phase | Plans | What |
|-------|-------|------|
| 1. Content Pipeline | 3/3 | Multi-format intake, SQLite + markdown sync, summary menu |
| 2. Memory & Surfacing | 2/2 | Explicit preferences, surfacing with topic scoring, rejection warnings |
| 3. Intelligence Layer | 2/2 | Embedding-based conflict detection, gap detection with targeting questions |
| 4. Research on Demand | 1/1 | Tavily API integration, targeting questions, cited results |

**88 tests passing. All requirements complete.**
