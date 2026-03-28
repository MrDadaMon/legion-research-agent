import yaml
import re
from pathlib import Path
from datetime import datetime

from src.models import ContentItem


def slugify_for_obsidian(name: str) -> str:
    """Convert a name to an Obsidian-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "untitled"


class ObsidianNote:
    """Represents an Obsidian markdown note with frontmatter and body."""

    def __init__(
        self,
        item: ContentItem,
        topic_slug: str,
        tags: list[str] | None = None,
        related_ids: list[int] | None = None,
        related_titles: dict[int, str] | None = None,
    ):
        self.item = item
        self.topic_slug = topic_slug
        self.tags = tags or []
        self.related_ids = related_ids or []
        self.related_titles = related_titles or {}

    def to_yaml_frontmatter(self) -> str:
        """Build YAML frontmatter block."""
        fm = {
            "id": self.item.id,
            "title": self.item.title,
            "source_type": self.item.source_type,
            "source_url": self.item.source_url,
            "topic": self.topic_slug,
            "processed_date": self.item.processed_date,
            "content_hash": self.item.content_hash,
            "tags": self.tags,
            "related": [
                {
                    "id": rid,
                    "title": self.related_titles.get(rid, f"Note {rid}"),
                    "link": f"[[{slugify_for_obsidian(self.related_titles.get(rid, str(rid)))}-{rid}]]",
                }
                for rid in self.related_ids
            ],
        }
        lines = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return f"---\n{lines}---\n"

    def to_markdown_body(self) -> str:
        """Build markdown body with [[links]] to related content."""
        lines = [f"# {self.item.title}", ""]

        if self.tags:
            tag_str = " ".join(f"#{tag}" for tag in self.tags)
            lines.append(f"{tag_str}")
            lines.append("")

        if self.item.source_url:
            lines.append(f"**Source:** [{self.item.source_url}]({self.item.source_url})")
            lines.append("")

        lines.append(f"**Type:** {self.item.source_type}")
        lines.append(f"**Processed:** {self.item.processed_date}")
        lines.append("")

        if self.related_ids:
            lines.append("## Related")
            lines.append("")
            for rid in self.related_ids:
                title = self.related_titles.get(rid, f"Note {rid}")
                slug = slugify_for_obsidian(title)
                lines.append(f"- [[{slug}-{rid}|{title}]]")
            lines.append("")

        lines.append("## Content")
        lines.append("")
        lines.append(self.item.raw_content)

        return "\n".join(lines)

    def to_string(self) -> str:
        """Full note as string with frontmatter + body."""
        return self.to_yaml_frontmatter() + self.to_markdown_body()


class ObsidianStore:
    """Obsidian vault store — writes properly linked markdown notes.

    Vault structure:
      vault/
        content/           # Individual content notes
          {slug}-{id}.md
        topics/           # Topic index notes
          {topic-slug}/
            index.md
        sessions/         # Daily research session logs
          {YYYY-MM-DD}.md
    """

    def __init__(self, vault_path: str = "knowledge/vault"):
        self.vault_path = Path(vault_path)
        self.content_dir = self.vault_path / "content"
        self.topics_dir = self.vault_path / "topics"
        self.sessions_dir = self.vault_path / "sessions"

    def _content_path(self, topic_slug: str, content_id: int, title: str) -> Path:
        slug = slugify_for_obsidian(title)
        return self.content_dir / f"{slug}-{content_id}.md"

    def _topic_index_path(self, topic_slug: str) -> Path:
        return self.topics_dir / topic_slug / "index.md"

    def _session_path(self, date_str: str) -> Path:
        return self.sessions_dir / f"{date_str}.md"

    async def ensure_dirs(self) -> None:
        """Ensure all vault directories exist."""
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.topics_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        item: ContentItem,
        topic_slug: str = "general",
        tags: list[str] | None = None,
        related_ids: list[int] | None = None,
        related_titles: dict[int, str] | None = None,
    ) -> Path:
        """Save a content item as an Obsidian note with [[links]]."""
        await self.ensure_dirs()

        note = ObsidianNote(
            item=item,
            topic_slug=topic_slug,
            tags=tags,
            related_ids=related_ids,
            related_titles=related_titles,
        )

        file_path = self._content_path(topic_slug, item.id, item.title)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(note.to_string())

        return file_path

    async def load(self, topic_slug: str, content_id: int) -> ContentItem | None:
        """Load a content item from its Obsidian note."""
        topic_dir = self.topics_dir / topic_slug
        if not topic_dir.exists():
            return None

        for md_file in topic_dir.glob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                parts = content.split("---", 2)
                if len(parts) < 3:
                    continue
                fm = yaml.safe_load(parts[1])
                if fm and fm.get("id") == content_id:
                    return self._note_to_content(fm, parts[2])
            except Exception:
                continue
        return None

    def _note_to_content(self, fm: dict, body: str) -> ContentItem:
        raw = body.strip()
        if raw.startswith(f"# {fm.get('title', '')}"):
            raw = raw[len(f"# {fm.get('title', '')}"):].strip()
        return ContentItem(
            id=fm.get("id"),
            source_type=fm.get("source_type", "unknown"),
            source_url=fm.get("source_url"),
            title=fm.get("title", "Untitled"),
            raw_content=raw,
            processed_date=fm.get("processed_date", datetime.now().isoformat()),
            content_hash=fm.get("content_hash", ""),
            reference_count=fm.get("reference_count", 1),
        )

    async def delete(self, topic_slug: str, content_id: int, title: str) -> bool:
        """Delete a content note."""
        file_path = self._content_path(topic_slug, content_id, title)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def create_topic_index(
        self,
        topic_slug: str,
        topic_name: str,
        content_items: list[ContentItem],
    ) -> Path:
        """Create or update a topic index note linking to all content."""
        await self.ensure_dirs()

        topic_dir = self.topics_dir / topic_slug
        topic_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._topic_index_path(topic_slug)

        lines = [
            "---",
            f"topic: {topic_name}",
            f"slug: {topic_slug}",
            f"content_count: {len(content_items)}",
            "---",
            "",
            f"# {topic_name}",
            "",
            f"This topic contains {len(content_items)} piece(s) of content.",
            "",
            "## Content",
            "",
        ]

        for item in content_items:
            slug = slugify_for_obsidian(item.title)
            lines.append(f"- [[{slug}-{item.id}|{item.title}]]")

        lines.append("")
        lines.append("## Notes")
        lines.append("")
        lines.append("<!-- Add your notes about this topic here -->")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return file_path

    async def create_daily_session(
        self,
        date_str: str | None = None,
        summary: str = "",
        content_ids: list[int] | None = None,
        research_query: str | None = None,
    ) -> Path:
        """Create a daily research session note.

        Args:
            date_str: YYYY-MM-DD format. Defaults to today.
            summary: Brief summary of the research session.
            content_ids: List of content IDs consumed during this session.
            research_query: The research question that triggered this session.
        """
        await self.ensure_dirs()

        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        file_path = self._session_path(date_str)
        existing = ""
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                existing = f.read()

        lines = []
        if existing:
            lines.append(existing)
            lines.append("")
            lines.append(f"## Session: {datetime.now().strftime('%H:%M')}")
        else:
            lines.append("---")
            lines.append(f"date: {date_str}")
            lines.append("---")
            lines.append("")
            lines.append(f"# Research Session: {date_str}")

        if research_query:
            lines.append("")
            lines.append(f"**Research Query:** {research_query}")

        if summary:
            lines.append("")
            lines.append(f"**Summary:** {summary}")

        if content_ids:
            lines.append("")
            lines.append("### Content Consumed")
            lines.append("")
            for cid in content_ids:
                lines.append(f"- [[content/{cid}|Note {cid}]]")

        lines.append("")
        lines.append("### Notes")
        lines.append("")
        lines.append("<!-- Session notes go here -->")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return file_path

    async def append_to_daily_session(
        self,
        entry: str,
        date_str: str | None = None,
    ) -> Path:
        """Append an entry to today's daily session note."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return await self.create_daily_session(date_str=date_str, summary=entry)

    async def list_topics(self) -> list[str]:
        """List all topic slugs in the vault."""
        if not self.topics_dir.exists():
            return []
        return [d.name for d in self.topics_dir.iterdir() if d.is_dir()]

    async def list_content_files(self) -> list[Path]:
        """List all content note files."""
        if not self.content_dir.exists():
            return []
        return list(self.content_dir.glob("*.md"))

    async def list_session_files(self) -> list[Path]:
        """List all session note files sorted by date."""
        if not self.sessions_dir.exists():
            return []
        return sorted(self.sessions_dir.glob("*.md"))
