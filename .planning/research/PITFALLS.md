# Pitfalls Research

**Domain:** Persistent Research Analyst Agent (Personal Knowledge Management with AI)
**Researched:** 2026-03-26
**Confidence:** MEDIUM

Research on 10 common pitfalls for a persistent research agent that stores content in SQLite + markdown, tracks preferences, and surfaces knowledge. Web search verification was limited due to search API issues, so findings are based on established patterns in knowledge management, RAG systems, and preference learning literature.

---

## Critical Pitfalls

### Pitfall 1: SQLite Locking with Multiple Writers

**What goes wrong:**
Processes crash with "database is locked" errors. The agent hangs when one process is writing while another tries to read or write. WAL (Write-Ahead Logging) checkpoint failures cause data corruption or lost writes.

**Why it happens:**
SQLite defaults to rollback journal mode, which uses exclusive locking during writes. When multiple processes (the main agent loop, a background processor, a surfacing query) access the database simultaneously, they block each other. The WAL checkpoint process requires exclusive access to finalize writes.

**How to avoid:**
- Enable WAL mode: `PRAGMA journal_mode=WAL;` - allows concurrent reads with one writer
- Set busy timeout: `PRAGMA busy_timeout=5000;` - wait 5s instead of immediate failure
- Use Write-Ahead Logging checkpoints strategically - run `PRAGMA wal_checkpoint(PASSIVE)` for non-blocking checkpoints during normal operation
- Serialize write operations through a single connection pool or queue
- Keep write transactions short - commit immediately after each operation

**Warning signs:**
- "database is locked" errors appearing in logs
- Queries timing out intermittently
- CPU spike on database file during reads
- WAL file growing unbounded (>100MB)

**Phase to address:**
Phase 2 (Core Storage Infrastructure) - must be solved before any multi-process architecture

---

### Pitfall 2: Embedding Drift When Model Changes

**What goes wrong:**
Search quality degrades after weeks or months. Similar queries return worse results over time. The knowledge base feels "lost" - relevant content surfaces poorly.

**Why it happens:**
Embeddings are dense vectors specific to the model that generated them. If the embedding model version changes (OpenAI updates, switching models), old embeddings and new embeddings live in different vector spaces. Cosine similarity between old and new vectors becomes meaningless.

**How to avoid:**
- Pin the embedding model to a specific version (e.g., "text-embedding-3-small" not "latest")
- Store model version in content metadata: `embedding_model: "text-embedding-3-small-2024-01-09"`
- Create a re-embedding migration pipeline when model must change
- Consider using a vector database (Qdrant, ChromaDB) instead of SQLite for embedding storage - they support batch re-embedding
- If staying with SQLite: store embeddings as BLOB, flag records needing re-embedding when model changes

**Warning signs:**
- Search results degrading over time without corpus changes
- Mixed results quality within same query session
- Embedding API returning different dimension counts
- Model deprecation notices from provider

**Phase to address:**
Phase 2 (Storage) and Phase 4 (Intelligence Layer) - architecture decision in Phase 2, implementation in Phase 4

---

### Pitfall 3: Preference Profile - Noisy vs. Sparse Signals

**What goes wrong:**
The preference profile becomes useless in two opposite ways:
- **Too noisy:** Every interaction is tracked, flooding the profile with low-signal data (clicked once = "likes X")
- **Too sparse:** Only explicit reactions stored, leaving the profile with almost no data after weeks

**Why it happens:**
- Noisy: treating all signals equally, no decay, no confidence weighting
- Sparse: waiting for explicit "like/dislike" reactions that users rarely give

**How to avoid:**
- Use an **explicit confirmation loop**: "Should I remember that you liked this?" - explicit signals > implicit
- Implement **signal decay**: preferences older than 30 days have reduced weight
- Distinguish **interaction types** with different weights:
  - Explicit "save/like" = high weight (1.0)
  - Asked follow-up = medium weight (0.5)
  - Just consumed (watched/read) = low weight (0.1)
  - Rejected/explicit skip = negative weight
- Cap total preference entries (e.g., max 500 signals) - prioritize recency and confidence
- Periodically ask "Are you still interested in X?" to validate old signals

**Warning signs:**
- Profile contains >1000 entries (likely noisy)
- Profile has <20 entries after 2 weeks (likely sparse)
- "Inconsistent preferences" surfacing - agent recommends what user rejected
- User saying "that's not what I meant"

**Phase to address:**
Phase 3 (Preference Tracking) - requires iterative tuning in Phase 5 (Polish)

---

### Pitfall 4: Gap Detection Firing Too Aggressively

**What goes wrong:**
The agent constantly interrupts with "I notice you have 3+ pieces on topic X - want more?" even when user is actively collecting. User gets annoyed and starts ignoring gap notifications, then misses legitimate ones.

**Why it happens:**
Gap detection triggers on a simple threshold (3+ pieces + 24h idle) without considering:
- User is mid-research session (not idle)
- User explicitly said "collecting these for later"
- The 3+ pieces are disparate topics with same keyword
- User already has enough on that topic

**How to avoid:**
- Track a "research session" state - don't fire during active intake
- Add explicit "I'm still researching X" mode that suppresses gap detection
- Require higher threshold for topics user recently interacted with (5+ pieces, 72h)
- Store whether user has explicitly said "I have enough on X" or "don't suggest more on X"
- Distinguish "same topic" vs "same keyword" - check semantic similarity, not just topic tag
- Let user configure sensitivity: "quiet mode" suppresses all gap detection

**Warning signs:**
- User frequently dismisses gap notifications
- Gap notification on topic user just added content to
- "Stop suggesting things" feedback
- Gap detection firing within hours of new content

**Phase to address:**
Phase 3 (Intelligence Features) - requires user feedback loop to tune

---

### Pitfall 5: Markdown/SQLite Sync Drift

**What goes wrong:**
SQLite has a record that doesn't have a corresponding markdown file, or vice versa. Content summaries in markdown differ from what's in SQLite. Deleted content still appears in search.

**Why it happens:**
Two storage systems updated at different times, or one update fails. Common scenarios:
- SQLite write succeeds, markdown write fails (disk full, permissions)
- User manually edits markdown (unsynced)
- Content deleted from SQLite but markdown remains
- Migration script modifies one but not the other

**How to avoid:**
- **Transactional consistency**: wrap SQLite and file writes in same operation with rollback
- Use SQLite as source of truth - markdown is derived, rebuild-able
- Store hash/checksum of markdown content in SQLite
- Run sync verification: periodic job that confirms all markdown files match SQLite records
- Log all operations to both systems with same transaction ID
- On startup: verify consistency, repair or rebuild from SQLite if needed

**Warning signs:**
- Markdown file exists with no matching SQLite record (query returns empty)
- SQLite record exists but markdown file missing (404 on file read)
- Content hash mismatch between SQLite metadata and actual file
- Search returns result that can't be opened

**Phase to address:**
Phase 2 (Core Storage) - must have consistency guarantees before Phase 3

---

### Pitfall 6: Large Content Blocking Processing

**What goes wrong:**
A 2-hour video or 500-page PDF causes the agent to hang for minutes or hours during processing. Other content waits. Agent appears frozen.

**Why it happens:**
Content extraction runs synchronously in the main processing pipeline. Large files are processed entirely before any result is returned. No streaming, no chunking, no prioritization.

**How to avoid:**
- **Streaming/chunked processing**: process video in segments, return progress incrementally
- **Size limits**: reject or warn on content >500MB
- **Priority queue**: short content (articles, short videos) jump ahead of long content
- **Background processing with callbacks**: large files queued for background processing, user notified when done
- **Chunked storage**: store video in segments (5-min chunks), create embeddings per chunk
- **Timeout enforcement**: if extraction exceeds 10 minutes, pause and report progress

**Warning signs:**
- Processing log shows same content for >5 minutes
- Memory usage spike during large file processing
- "Processing..." status never completing
- Other queued items not being processed

**Phase to address:**
Phase 2 (Content Intake Pipeline) - must be non-blocking from day one

---

### Pitfall 7: Storing Duplicate Content

**What goes wrong:**
Same article/video stored 3 times under different URLs or with slightly different titles. Search returns near-identical results. Knowledge base bloat. Confused comparisons ("which one was the one you liked?").

**Why it happens:**
- Same content linked from different URLs (YouTube, blog mirror, archive.org)
- Slight title variations ("How to X" vs "How to X - Complete Guide")
- Re-processing same content after user re-pastes link
- Content from different sources on same topic (not duplicates, but overlapping)

**How to avoid:**
- **Content fingerprinting**: generate hash of extracted text content (not URL)
- **URL deduplication**: normalize URLs (remove tracking params, www vs non-www)
- **Title normalization**: strip suffixes like "- YouTube", "| Blog"
- **Similarity check on intake**: if new content has >90% overlap with existing, prompt user
- **One-true-copy pattern**: if duplicate detected, link to existing record instead of new entry
- Store canonical URL, all alternate URLs as aliases

**Warning signs:**
- Search results showing very similar content repeatedly
- Intake prompt "This looks similar to X - still store?"
- Database growing faster than expected given intake rate
- Disk usage higher than calculated from content sizes

**Phase to address:**
Phase 2 (Content Intake) - deduplication check at point of intake

---

### Pitfall 8: Preference Misreads

**What goes wrong:**
Agent thinks user rejected something when they didn't (and vice versa). User says "I never said I disliked that." Agent avoids surfacing content user would have wanted. Trust erodes.

**Why it happens:**
- Ambiguous user signals interpreted as preferences:
  - "Not now" = "not interested" (should mean "defer, not reject")
  - "Skip" on gap detection = "I don't want more" (should just mean "not now")
  - Scrolling past something in surfacing results = "not relevant" (should be ignored)
- Inferred preferences from consumption (watched = liked, but user was just curious)
- No distinction between "tried and disliked" vs "never wants to see"

**How to avoid:**
- **Explicit over implicit**: prefer asking "should I remember this?" rather than inferring
- **Distinguish defer from reject**: "not now" creates a defer marker, not a negative signal
- **Require confirmation for negative signals**: "It seems you rejected X - should I mark that?"
- **Provide undo**: all preferences can be revised, with clear UI to do so
- **Log confidence level**: low-confidence inferences vs high-confidence explicit signals
- **Never auto-reject**: only surface explicit rejections in "don't show this again" mode

**Warning signs:**
- User saying "I didn't reject that"
- Agent refusing to surface content user clearly would want
- Preferences table has many recent entries with low confidence
- User frequently revising preferences

**Phase to address:**
Phase 3 (Preference Tracking) - needs user feedback mechanism throughout

---

### Pitfall 9: Cold Start - No Prior Knowledge

**What goes wrong:**
New user (or fresh install) gets no value because the agent has nothing to personalize from. No basis for surfacing, no preferences, no topic history. Early impressions determine whether user sticks around.

**Why it happens:**
System designed for accumulation over time, not for initial state. Cold start is especially harsh because:
- No preference signals = generic surfacing
- No topic history = no basis for gap detection
- Empty knowledge base = no search results
- Agent has nothing to compare "new" content against

**How to avoid:**
- **Welcome flow**: ask user 3-5 topics they care about initially
- **Import existing knowledge**: option to import bookmarks, reading list, past notes
- **Conservative initial surfacing**: don't guess, show recent intake prominently
- **Exploit not explore**: early on, surface content matching stated interests aggressively
- **Onboarding content**: include 3-5 curated pieces to seed topic understanding
- **Topic seeds**: use user-stated interests to create initial topic embeddings for matching
- **Don't pretend to know**: be transparent that the agent is learning - "I don't know your preferences yet"

**Warning signs:**
- New install with no intake after 24h (user lost interest)
- Preference table still empty after 1 week
- Surfacing results identical regardless of user (no personalization)
- User asking "how do I get started?"

**Phase to address:**
Phase 1 (Agent Foundation) - onboarding must be in initial release

---

### Pitfall 10: Memory Bloat as Knowledge Base Grows

**What goes wrong:**
Search becomes slow (>2 seconds). SQLite file is >1GB. Agent consumes excessive RAM. Processing overhead makes real-time features sluggish.

**Why it happens:**
- No pagination on queries - loads entire result sets
- Embedding vectors stored inefficiently (not compressed)
- Full-text search indexes not maintained
- No archival of old/dead content
- WAL file not checkpointing (from Pitfall 1)
- No query optimization as dataset grows

**How to avoid:**
- **Pagination everywhere**: never load more than 50 items per query
- **Efficient embedding storage**: if using SQLite, store as BLOB not TEXT (4x smaller)
- **Archive old content**: content not accessed in 90 days → compressed archive
- **Maintain indexes**: FTS index on content, index on topic, created_at, last_accessed
- **Regular VACUUM**: `PRAGMA vacuum;` to reclaim space monthly
- **Query limits**: always include `LIMIT` and `OFFSET` in queries
- **Monitor growth**: alert if KB grows >10% week-over-week without intake
- **Content lifecycle**: delete content user explicitly rejects (not just mark)

**Warning signs:**
- Search latency >1 second
- Database file >500MB
- RAM usage >2GB for agent process
- `VACUUM` not run in >30 days
- WAL file >100MB

**Phase to address:**
Phase 2 (Storage Infrastructure) - design for scale from start

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|------------------|
| Skip content fingerprinting (dupe check) | Faster intake | Duplicates bloat KB, confuse surfacing | Never - too costly to fix later |
| Store embeddings as TEXT in SQLite | Simpler implementation | 4x storage, slower queries | Phase 1 only, migrate in Phase 2 |
| Single-threaded writes | Simpler code | Slow intake under load | Phase 1 only, add queue in Phase 2 |
| No WAL mode (default journal) | Works out of box | Locking errors with concurrent access | Phase 1 only, WAL in Phase 2 |
| Store markdown as JSON (single file) | Simple sync | Single point of failure, no partial reads | Never - use directory per content |
| Skip content hash verification | Faster writes | Silent corruption undetected | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| YouTube | Assuming video URL stable | Store canonical video ID, handle deleted/moved |
| Web articles | Not handling paywalls | Detect and warn, don't store garbage |
| PDFs | Not handling scanned images | Use OCR-capable parser, warn if image-only |
| Exa/API (search) | No rate limiting | Queue requests, respect limits |
| video-to-knowledge | No timeout | 10min timeout per video, chunk processing |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unbounded query results | Memory spike, slow renders | Always LIMIT 50 | >1000 total records |
| No query indexes | Search >1s at 10k records | Index on topic, created_at, last_accessed | >5000 records |
| WAL never checkpointing | WAL file >1GB | Passive checkpoint daily | >100MB WAL |
| No content archival | Database >1GB | Archive after 90 days inactive | >500MB DB |
| Embedding everything | Slow intake, high API cost | Only embed when surfacing needed | >1000 pieces |
| Full re-embed on model change | Days of processing | Batch migration, background job | Any model change |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing API keys in markdown | Key exposure if repo shared | .env only, .gitignore |
| Content from untrusted sources | Malware via scraped JS | Sanitize HTML, no script execution |
| Storing user preference patterns | Preference leakage | Encrypt sensitive preference fields |
| No input validation on intake | Injection via crafted content | Sanitize all extracted content |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Agent silent on unknowns | User doesn't know agent is uncertain | "I'm not sure I have anything on X - want me to search?" |
| Gap detection interrupting | Breaks flow during active research | Only fire during idle, with "dismiss for now" |
| Surface everything matching | Overwhelming results | Rank by recency + preference match, show top 5 |
| Ask too many preference questions | Annoying onboarding | Max 3 questions initially, defer rest |
| Not explaining why surfaced | Feels random | "Surfacing this because you liked X" |

---

## "Looks Done But Isn't" Checklist

- [ ] **SQLite WAL**: Enabling WAL mode is not enough - must also handle checkpoint failures
- [ ] **Preference tracking**: Having a preferences table is not enough - must have decay and confidence weighting
- [ ] **Gap detection**: Having a threshold check is not enough - must check research session state
- [ ] **Deduplication**: Having a URL check is not enough - must also fingerprint content
- [ ] **Markdown sync**: Writing both systems is not enough - must have consistency verification
- [ ] **Cold start**: Asking onboarding questions is not enough - must seed with initial content

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SQLite lock corruption | MEDIUM | Restore from WAL checkpoint, verify with `PRAGMA integrity_check;` |
| Embedding drift | HIGH | Batch re-embed all content, ~1 hour per 10k pieces |
| Markdown/SQLite drift | LOW | Rebuild markdown from SQLite (source of truth), verify with hash |
| Duplicate content | LOW | Run deduplication, merge or delete duplicates |
| Preference bloat | LOW | Implement decay, archive old signals, cap entries |
| Memory bloat | LOW | `VACUUM`, archive old content, add pagination |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SQLite locking | Phase 2 (Core Storage) | Concurrent read/write test with 3+ processes |
| Embedding drift | Phase 2 (Storage decision) + Phase 4 (Migration) | Pin model version, test re-embed pipeline |
| Preference noise/sparse | Phase 3 (Preferences) | User feedback survey at 2 weeks |
| Gap detection aggression | Phase 3 (Gap Detection) | Track dismiss rate, adjust thresholds |
| Markdown/SQLite drift | Phase 2 (Sync) | Startup consistency check, periodic verify |
| Large content blocking | Phase 2 (Intake Pipeline) | Process 2hr video without blocking other intake |
| Duplicate content | Phase 2 (Intake) | Test with same URL submitted twice |
| Preference misreads | Phase 3 (Preferences) + Phase 5 (Feedback) | User correction rate <5% |
| Cold start | Phase 1 (Foundation) | New install gets value in <5 minutes |
| Memory bloat | Phase 2 (Storage) + Phase 5 (Maintenance) | DB size stable relative to active content |

---

## Sources

- SQLite documentation: https://docs.python.org/3/library/sqlite3.html
- LangChain vector store documentation: https://docs.langchain.com/
- RAG system patterns: Established industry patterns (MEDIUM confidence)
- Preference learning: Established ML patterns (MEDIUM confidence)
- Personal knowledge management: Common patterns from Obsidian, Notion, Readwise (MEDIUM confidence)

*Note: Web search verification was limited during this research. Findings are based on established domain patterns. Recommend phase-specific deep dives when implementing each pitfall area.*

---
*Pitfalls research for: Persistent Research Analyst Agent*
*Researched: 2026-03-26*
