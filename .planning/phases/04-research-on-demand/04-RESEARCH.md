# Phase 4: Research on Demand - Research

**Researched:** 2026-03-26
**Domain:** Web research API integration, citation formatting, targeted search UX
**Confidence:** MEDIUM

## Summary

Phase 4 implements "find me more like this" functionality - when user requests research on any stored content, the agent asks 1-2 targeting questions, then performs web research and returns cited results. This phase ACTUALLY EXECUTES the web search that gap_handler.py currently just logs (see gap_handler.py line 253: "Note: Actual gap research is a v2 feature").

**Primary recommendation:** Use Tavily `/research` endpoint for cited web search. Reuse and generalize `ask_targeting_questions()` from gap_handler.py. Create shared research utilities.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RESEARCH-01 | User can say "find me more like this" on any stored content | Trigger detection pattern, embedding-based content identification |
| RESEARCH-02 | Agent asks 1-2 targeting questions before searching | Reuse gap_handler's targeting question flow |
| RESEARCH-03 | Results returned with citations, source URLs, and relevance explanation | Tavily API provides highlights + URLs; design citation format |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | latest | HTTP client for web search API calls | Already used in article_scraper.py |
| tavily-python | latest | Research API with built-in citations | DeepResearch benchmark leader, citations out-of-box |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | latest | Environment variable management | Already in config.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tavily | Exa AI | Exa has 70M+ sources but Tavily's `/research` endpoint is purpose-built for AI agents with citations |
| Tavily | SerpAPI/Google | More traditional, less AI-optimized, no highlights feature |
| Tavily | DuckDuckGo | Free but no citation support, no relevance scores |

**Installation:**
```bash
pip install tavily-python requests python-dotenv
```

## Key Architecture Decisions

### 1. "Find Me More Like This" Flow

**NOT just similarity search in database.** This phrase means:
1. User selects a stored content item
2. System uses that content's topics/keywords as seed for EXTERNAL web research
3. Returns NEW content from the web, not just stored content

**Implementation:**
```
User triggers "find me more like this" on content_id=X
  → Get stored content item
  → Extract topics, title, key terms from content
  → Ask targeting questions (reuse gap_handler pattern)
  → Build search query from content + answers
  → Call Tavily /research endpoint
  → Format results with citations
  → Present to user
```

### 2. Code Sharing with Gap Handler

**Gap Handler currently:**
- `ask_targeting_questions()` - asks what aspect user wants (reuse)
- `generate_gap_research()` - generates search queries (NEED TO REPLACE with actual API call)
- `present_gap_results()` - shows results with accept/reject (reuse with modification)

**Recommendation:** Create shared `research_utils.py` with:
- `ask_research_targeting_questions()` - generalized from gap_handler
- `execute_web_research()` - Tavily API call
- `format_cited_results()` - citation formatting

Gap handler imports from shared utils instead of its own `generate_gap_research()`.

### 3. Citation Format

Plain text with URLs (not BibTeX/APA - too complex for v1):

```
**Result 1: [Title]**
Source: [URL]
Relevance: [score/explanation]
Key finding: [highlight excerpt from Tavily]

---
**Result 2: [Title]**
...
```

Each result includes:
- Title
- Source URL
- Relevance explanation (what makes this relevant to the query)
- Key highlight (relevant excerpt from Tavily)

### 4. Targeting Questions Design

Based on gap_handler.py pattern (lines 140-177), but refined:

**Question 1: Aspect refinement**
"What specific aspect of '[topic]' are you most interested in?"
- Options derived from stored content analysis
- "General overview" as fallback
- "Other" with free text

**Question 2: Specific focus (optional)**
"Is there anything specific you want to find?"
- Free text, can skip with Enter
- Used to refine search query

### 5. Trigger Detection Pattern

Add to surfacing_handler.py or create research_handler.py with:

```python
RESEARCH_TRIGGER_PATTERNS = [
    r'find\s+me\s+more\s+like\s+this',
    r'search\s+for\s+more\s+on',
    r'research\s+more\s+on',
    r'look\s+up\s+more\s+about',
    r'get\s+more\s+info\s+on',
]
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Web search with citations | Custom search + scraping | Tavily /research endpoint | Built-in highlights, relevance scores, citation formatting |
| Similar content identification | New embedding logic | Reuse embedding_store.find_similar_on_topic() | Already exists, works well |
| Targeting questions | Custom flow | Reuse/extend gap_handler.ask_targeting_questions() | Already built and tested |

## Common Pitfalls

### Pitfall 1: Forgetting "Stored Content" Context
**What goes wrong:** Agent searches the web but doesn't connect results back to user's existing knowledge base.
**How to avoid:** Always show "Related to your stored content: [title]" when presenting research trigger.
**Warning signs:** User says "but I already know that" or results seem generic.

### Pitfall 2: API Key Management
**What goes wrong:** Hardcoding Tavily API key or not loading from .env.
**How to avoid:** Use existing `load_dotenv()` pattern from config.py. Add `TAVILY_API_KEY` to .env.example.
**Warning signs:** API errors, key exposure in logs.

### Pitfall 3: Overwhelming Results
**What goes wrong:** Returning 10+ results with full highlights overwhelms user.
**How to avoid:** Limit to 3-5 results per research request. Show top result first with "Show more?" option.
**Warning signs:** User ignores research results or asks to "make it shorter."

### Pitfall 4: Generic Search Queries
**What goes wrong:** Using only the stored content title as query, getting generic results.
**How to avoid:** Combine: stored content topics + user's targeting question answers → composite query.
**Warning signs:** Results match the original content exactly (not NEW information).

## Code Examples

### Trigger Detection (surfacing_handler.py pattern)

```python
# Add to surfacing_handler.py
RESEARCH_TRIGGER_PATTERNS = [
    r'find\s+me\s+more\s+like\s+this',
    r'search\s+for\s+more\s+on',
]

def is_research_query(user_message: str) -> bool:
    """Detect if user is requesting research on stored content."""
    user_lower = user_message.lower().strip()
    for pattern in RESEARCH_TRIGGER_PATTERNS:
        if re.search(pattern, user_lower):
            return True
    return False

def extract_content_reference(user_message: str) -> str | None:
    """Extract content reference from 'find me more like this on X'."""
    # Pattern: "find me more like this" (refers to currently discussed content)
    # or "find me more like this on [topic]"
    match = re.search(r'find\s+me\s+more\s+like\s+this\s+on\s+(.+?)(?:\?|$)', user_message)
    if match:
        return match.group(1).strip()
    return None  # None = use currently selected/discussed content
```

### Tavily Research Call

```python
from tavily import TavilyClient
import os

async def execute_research(query: str, api_key: str | None = None) -> dict:
    """Execute web research using Tavily /research endpoint."""
    key = api_key or os.getenv("TAVILY_API_KEY")
    if not key:
        raise ValueError("TAVILY_API_KEY not set in environment")

    client = TavilyClient(api_key=key)

    # Use research endpoint for comprehensive results with citations
    result = client.research(
        query=query,
        max_results=5,
        include_answer=True,  # AI-generated answer summary
        include_highlights=True,  # Relevant excerpts
    )

    return result
```

### Citation Formatting

```python
def format_research_results(tavily_results: dict) -> str:
    """Format Tavily research results into cited output."""
    output = ["[Research Results]\n"]

    for i, result in enumerate(tavily_results.get("results", []), 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")
        highlights = result.get("highlights", [])

        output.append(f"**{i}. {title}**")
        output.append(f"Source: {url}")

        if highlights:
            output.append(f"Key finding: {highlights[0][:200]}...")
        elif content:
            output.append(f"Summary: {content[:200]}...")

        output.append("")

    # Add AI answer if present
    if tavily_results.get("answer"):
        output.extend(["---", f"**AI Summary:** {tavily_results['answer']}"])

    return "\n".join(output)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule-based search query generation (gap_handler.generate_gap_research) | Tavily /research API | Phase 4 | Actual web search instead of mock queries |
| No citation support | Built-in highlights + URLs from Tavily | Phase 4 | Meets RESEARCH-03 requirement |

**Deprecated/outdated:**
- gap_handler.generate_gap_research() - currently just logs, Phase 4 replaces with actual API call

## Open Questions

1. **Should research results be stored?**
   - What we know: Gap handler stores "interest" but doesn't store results
   - What's unclear: Should "find me more like this" results be saved to knowledge base?
   - Recommendation: v1 - NO, just display. v2 - could offer "save top result"

2. **How to handle "find me more like this" when no content is selected?**
   - What we know: User might say this without specifying which content
   - What's unclear: Should it ask "which content?" or use most recent?
   - Recommendation: Ask "which content would you like me to find more like?"

3. **Should we use Deep Search or regular search?**
   - What we know: Tavily has both `search()` and `research()` endpoints
   - What's unclear: Is `research()` worth the extra time/cost for "find me more like this"?
   - Recommendation: Use `research()` since it's built for AI agents and citations are important

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | pytest.ini (none detected - check project root) |
| Quick run command | `pytest tests/test_research_handler.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| RESEARCH-01 | Trigger detection | unit | `pytest tests/ -k "test_research_trigger" -x` | NO - Wave 0 needed |
| RESEARCH-01 | Content extraction for query | unit | `pytest tests/ -k "test_content_to_query" -x` | NO |
| RESEARCH-02 | Targeting questions asked | unit | `pytest tests/ -k "test_targeting_questions" -x` | NO |
| RESEARCH-03 | Citation formatting | unit | `pytest tests/ -k "test_citation_format" -x` | NO |

### Wave 0 Gaps
- [ ] `tests/test_research_handler.py` - trigger detection, query building, citation formatting
- [ ] `tests/conftest.py` - shared fixtures (mock Tavily responses)
- [ ] Framework install: `pip install pytest pytest-asyncio tavily-python` (if not in requirements.txt)

## Sources

### Primary (HIGH confidence)
- Tavily API documentation (https://tavily.com) - research endpoint features, citations, highlights
- gap_handler.py lines 140-177 - existing targeting question pattern
- embedding_store.py - existing similarity search to reuse

### Secondary (MEDIUM confidence)
- Exa AI documentation (https://exa.ai) - alternative search API comparison

### Tertiary (LOW confidence)
- Web search for "research API citations" - unverified, used general knowledge

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - Tavily is well-documented, alternatives exist
- Architecture: HIGH - reusing existing patterns from gap_handler
- Pitfalls: MEDIUM - based on gap_handler implementation patterns

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (30 days - search API space is relatively stable)
