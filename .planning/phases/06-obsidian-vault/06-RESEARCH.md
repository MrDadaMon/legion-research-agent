# Phase 06 Research — Obsidian Vault Integration

## What This Is
Replace the plain `knowledge/` folder (markdown files) with an Obsidian vault. Obsidian vault is still a folder of markdown files, but with proper `[[double bracket links]]`, YAML frontmatter, and visual knowledge graph.

## Obsidian Conventions to Implement
1. **Double bracket links**: `[[note-name]]` — creates link to another note
2. **Embeds**: `![[note-name]]` — embeds content of another note
3. **Tags**: `#tag` inline tags
4. **YAML frontmatter**: `---` delimited metadata at top of each file
5. **Daily notes**: `YYYY-MM-DD` dated research session notes
6. **Backlinks**: Each note tracks what links TO it (for context)

## ObsidianStore Class
Extends/replaces MarkdownStore:
- `save(content_item, linked_topics)` — writes markdown with `[[links]]` to related content
- `create_daily_note(date, summary)` — creates dated research session note
- `update_backlinks(content_id)` — updates backlinks index
- `search_by_link(topic)` — find content linked to a topic

## Graph Relationships
- Each content piece = one Obsidian note
- Topics = folders with index notes
- Cross-links between related content (via embedding store similarity)
- Daily notes = research session logs linking to content consumed

## Key Files
- `src/storage/obsidian_store.py` (new — replaces MarkdownStore interface)
- `src/storage/backlinks_index.py` (new — tracks backlinks)
- `src/config.py` (add OBSIDIAN_VAULT_PATH)

## Vault Structure
```
vault/
  content/           # Individual content notes
    video-123.md
    article-456.md
  topics/            # Topic index notes
    trading-bots/
      index.md       # Overview + linked content
  sessions/          # Daily research session logs
    2026-03-27.md
  .obsidian/
    .gitkeep         # Obsidian config marker (no real .obsidian needed)
```

## Deferred
- Obsidian plugins (local REST API, various plugins) — not needed for core
- Cloud sync — manual backup only
