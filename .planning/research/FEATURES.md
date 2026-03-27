# Feature Research

**Domain:** Persistent personal research analyst agent
**Researched:** 2026-03-26
**Confidence:** MEDIUM

*Note: WebSearch was unavailable during research. Findings based on training data knowledge of the PKM/AI agent landscape. Competitive claims should be verified with current user research.*

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels broken or primitive.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-format content intake | Users paste links from YouTube, articles, PDFs, raw text. If any type fails, trust erodes immediately. | MEDIUM | Requires working extraction for each source type. YouTube is hardest (transcript API variability). |
| Content extraction (transcript/text + metadata) | Without extracted content, nothing can be stored or searched. Metadata (title, author, date, source URL) makes content usable. | MEDIUM | YouTube requires yt-dlp + transcript API. Articles need readability parsing. PDFs need OCR for scans. |
| Persistent storage (SQLite + markdown sync) | Users expect their data to survive restarts. Markdown backup means they can read/edit outside the agent. | LOW | SQLite for queries, markdown for human readability. Keep in sync on every write. |
| Topic-based content categorization | Finding content by "that video about trading bots" is more natural than "video file 47." Topics must be auto-detected or easily assigned. | MEDIUM | Can start with manual tagging, evolve to auto-tagging via LLM classification. |
| Content surfacing (pull from knowledge base) | The core promise: "ask about anything and get what you've seen before." Without this, it's just a fancy file storage box. | MEDIUM | Basic keyword search is table stakes. LLM-semantic search elevates it but is not required for v1. |
| Summary flow (quick / full / ask / save) | After intake, users need a next action. "What just happened?" is the first question. | LOW | Four clear options post-intake. Works as a simple menu or auto-detected based on content length. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but directly execute the core value proposition.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Rejected approach warnings | This is the agent "remembering your past." Most tools treat rejections as one-time events. This is what makes the agent feel like it knows you. Prevents wasted re-exploration of already-rejected paths. | MEDIUM | Requires storing rejection events with context and reasons. At query time, semantically match current intent against rejection history and surface a warning before proceeding. |
| Conflict detection and comparison | When two sources say different things, users feel stupid for not knowing. The agent actively catching conflicts and saying "you have two sources that disagree" is high-value. | HIGH | Requires embedding both sources and computing similarity. Threshold-based overlap detection (not just duplicate detection). Compare view shows key differences side-by-side. |
| Gap detection with targeting questions | "You've watched 5 videos on this topic in 2 days but nothing new?" This shows the agent is paying attention and cares about progress, not just storage. Turns passive collection into active research direction. | MEDIUM | Track content count per topic + timestamps. The 3+ content / 24h idle threshold is an initial heuristic -- should be tunable. The targeting questions (before surfacing) are the valuable part. |
| Research on demand with targeting questions | "Find me more like this" is common but most tools just search. Asking "what aspect of this do you want more of?" before searching produces dramatically better results. This is where the agent earns its title as "analyst" not "file cabinet." | HIGH | Requires the agent to extract key dimensions from the source material, generate 2-3 targeting questions, then search with those constraints. Citing results against sources is essential for trust. |
| Explicit preference memory with reason tracking | Most tools infer preferences from behavior (clicks, time spent). Explicit signals (user says "I liked this approach because X") are more reliable and actionable. Storing reasons (not just signals) enables the rejected approach warnings. | MEDIUM | Needs a schema: signal type (positive/negative/comparison), target (content ID or topic), reason (text), timestamp. Reason field is what makes this powerful for future warnings. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for this specific product.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Automatic proactive research | "Imagine if it just went out and found things for you!" | Without user direction, the agent will fill your knowledge base with irrelevant content. Worse: it surfaces gaps the user doesn't care about, creating noise and anxiety. | Research on demand (user initiates) is the right model. Add proactive later only if user explicitly opts in and defines topics of interest. |
| Multi-user support | "My partner could use this too!" | v1 is explicitly single-user. Multi-user adds auth, data isolation, preference conflicts, and shared state complexity. The agent's memory is personal -- that specificity is the value. | Ship v1 single-user. Multi-user is a v2+ consideration with explicit research on whether it conflicts with the personal memory model. |
| Remote access / cloud sync | "I want to use it from my phone!" | Remote access requires auth, TLS, and exposed ports -- all security and maintenance surface area. Cloud sync adds conflict resolution for markdown files, which is a hard problem. | Local-only is the right constraint. If remote access is needed later, use a purpose-built tunnel solution (Cloudflare Tunnel, ngrok) rather than building it in. |
| Automatic topic tagging (aggressive) | "Just organize everything automatically!" | LLM topic inference on every piece of content is slow and expensive. Auto-tags are often wrong, creating a messy taxonomy that users then have to clean up. | Start with manual tagging. Add auto-tagging as a suggestion system (show suggested tags, user confirms). Let the topic structure emerge from user behavior, not LLM assumptions. |
| Social sharing / export for others | "I want to share my research with my team!" | This is a fundamentally different product (team knowledge base vs personal memory). Building sharing UI, permissions, and collaborative features distracts from core value. | Don't build sharing. If genuinely needed, export individual markdown files or generate shareable summaries manually. |

## Feature Dependencies

```
Content Intake (auto-detect)
    └──requires──> Content Extraction (transcripts/text)
                        └──requires──> Storage (SQLite + markdown)
                                                └──requires──> Content Surfacing
                                                                        └──enhanced by──> Explicit Preference Memory
                                                                                              └──enables──> Rejected Approach Warnings
                                                └──enhanced by──> Conflict Detection

Summary Flow ──depends on──> Storage

Gap Detection ──depends on──> Storage + Topic Categorization + Preference Memory

Research on Demand ──depends on──> Storage + Content Surfacing + Targeting Questions
```

### Dependency Notes

- **Content Intake requires Extraction:** Cannot store what hasn't been extracted. Intake and extraction are a pipeline.
- **Storage requires Extraction:** Storage is downstream of the extraction pipeline.
- **Rejected Approach Warnings require Preference Memory:** Warnings are only possible if rejections were stored with reasons.
- **Gap Detection requires Storage + Topic Categorization:** Needs to count content per topic over time.
- **Conflict Detection enhances Content Surfacing:** Surfacing that also flags conflicts is more valuable than surfacing alone.
- **Research on Demand requires Content Surfacing:** Uses the same retrieval infrastructure but with active query construction.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what validates the core value proposition.

- [ ] **Content intake (multi-format)** -- paste any link or text, agent handles it. No manual format selection.
- [ ] **Content extraction** -- transcripts for video, text for articles, parsed content for PDFs, raw text stored as-is. Metadata captured.
- [ ] **Storage (SQLite + markdown, in sync)** -- everything persisted. Markdown files human-readable.
- [ ] **Summary flow** -- after intake, quick summary / full breakdown / ask question / save for later.
- [ ] **Content surfacing** -- "what did I watch about X?" returns relevant content with context.
- [ ] **Explicit preference tracking** -- user can say "remember I liked/didn't like this because X" and it sticks.

### Add After Validation (v1.x)

Once core loop works, add intelligence layers.

- [ ] **Rejected approach warnings** -- add after preference tracking is validated. Trigger when current query matches a past rejection.
- [ ] **Topic auto-tagging (suggested)** -- add after storage has 20+ items. Show suggested tags, user confirms or corrects.
- [ ] **Conflict detection (basic)** -- add after storage has multiple sources on same topics. Start with title/abstract similarity, graduate to semantic.

### Future Consideration (v2+)

Features requiring product-market fit before investing.

- [ ] **Gap detection with targeting questions** -- requires enough content history to be meaningful. Also needs careful UX to not be annoying.
- [ ] **Research on demand with targeting questions** -- requires the agent to reliably extract query dimensions and generate good targeting questions. Needs significant testing.
- [ ] **Auto-tagging (aggressive, LLM-driven)** -- only if manual tagging proves too burdensome and users want "it just works."
- [ ] **Proactive research (opt-in)** -- only if users explicitly ask for it. Must let user define topics of interest.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Content intake (multi-format) | HIGH | MEDIUM | P1 |
| Content extraction | HIGH | MEDIUM | P1 |
| Storage (SQLite + markdown) | HIGH | LOW | P1 |
| Summary flow | HIGH | LOW | P1 |
| Content surfacing | HIGH | MEDIUM | P1 |
| Explicit preference tracking | HIGH | MEDIUM | P1 |
| Rejected approach warnings | MEDIUM | MEDIUM | P2 |
| Topic categorization | MEDIUM | MEDIUM | P2 |
| Conflict detection | MEDIUM | HIGH | P2 |
| Gap detection | MEDIUM | MEDIUM | P2 |
| Research on demand | MEDIUM | HIGH | P3 |
| Auto-tagging | LOW-MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v1 launch
- P2: Should have, add when core is validated
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Readwise Reader | Notion AI | Obsidian + Plugins | Our Approach |
|---------|-----------------|-----------|-------------------|--------------|
| Multi-format intake | YES (app + web clipper) | YES (web clipper) | YES (various plugins) | Same -- auto-detect on paste |
| Content extraction | YES (transcripts, highlights) | Partial | Via plugins | Same -- yt-dlp, readability, pdf parsing |
| Storage | Cloud-only | Cloud + local | Local markdown | SQLite + markdown (LOCAL only) |
| Summary flow | YES (Ask feature) | YES | Via plugins | Same with user control |
| Content surfacing | YES (search + Ask) | YES (search) | YES (search + local REST API) | Same + persistent memory |
| Preference tracking | Implicit (reading stats) | NO | Via plugins | Explicit signals with reasons |
| Rejected approach warnings | NO | NO | NO | YES -- core differentiator |
| Conflict detection | NO | NO | NO | YES -- detect on overlap |
| Gap detection | NO | NO | NO | YES -- 3+ pieces / 24h idle |
| Research on demand | NO | NO | NO | YES -- targeting questions first |
| Local-only operation | NO | NO | YES | YES -- Legion host |

**Key competitive insight:** Every competitor focuses on collection and retrieval. None focus on the "reject / prefer / warn" memory loop. This is where the agent differentiates from being a fancy database to being a true research partner.

## Sources

- Readwise Reader product analysis (readwise.io/reader)
- Notion AI capabilities (notion.so)
- Obsidian plugins ecosystem (obsidian.md)
- Mem AI product (mem.ai)
- General PKM best practices literature
- Training data knowledge of AI agent landscape (MEDIUM confidence -- should verify with user research before making claims)

---
*Feature research for: Persistent research analyst agent*
*Researched: 2026-03-26*
