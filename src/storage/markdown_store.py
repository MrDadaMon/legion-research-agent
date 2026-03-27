import yaml
import re
from pathlib import Path

from src.models import ContentItem


class MarkdownStore:
    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = Path(knowledge_dir)

    def _topic_dir(self, topic_slug: str) -> Path:
        return self.knowledge_dir / topic_slug

    def _content_path(self, topic_slug: str, content_id: int) -> Path:
        return self.knowledge_dir / topic_slug / f"{content_id}.md"

    async def save(self, item: ContentItem, topic_slug: str = "general") -> None:
        topic_dir = self._topic_dir(topic_slug)
        topic_dir.mkdir(parents=True, exist_ok=True)

        file_path = self._content_path(topic_slug, item.id)

        frontmatter = {
            "id": item.id,
            "title": item.title,
            "source_type": item.source_type,
            "source_url": item.source_url,
            "topic": topic_slug,
            "processed_date": item.processed_date,
            "content_hash": item.content_hash,
            "reference_count": item.reference_count,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.safe_dump(frontmatter, f, default_flow_style=False, sort_keys=False)
            f.write("---\n")
            f.write(f"# {item.title}\n")
            f.write(item.raw_content)

    async def load(self, topic_slug: str, content_id: int) -> ContentItem | None:
        file_path = self._content_path(topic_slug, content_id)
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        frontmatter = yaml.safe_load(parts[1])
        raw_content = parts[2].strip()
        if raw_content.startswith(f"# {frontmatter['title']}"):
            raw_content = raw_content[len(f"# {frontmatter['title']}"):].strip()

        return ContentItem(
            id=frontmatter["id"],
            source_type=frontmatter["source_type"],
            source_url=frontmatter["source_url"],
            title=frontmatter["title"],
            raw_content=raw_content,
            processed_date=frontmatter["processed_date"],
            content_hash=frontmatter["content_hash"],
            reference_count=frontmatter["reference_count"],
        )

    async def delete(self, topic_slug: str, content_id: int) -> bool:
        file_path = self._content_path(topic_slug, content_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def list_topic_content(self, topic_slug: str) -> list[tuple[int, str]]:
        topic_dir = self._topic_dir(topic_slug)
        if not topic_dir.exists():
            return []

        results = []
        for md_file in topic_dir.glob("*.md"):
            try:
                content_id = int(md_file.stem)
                title = await self._get_title_from_file(md_file)
                results.append((content_id, title))
            except ValueError:
                continue
        return sorted(results)

    async def _get_title_from_file(self, file_path: Path) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            parts = content.split("---", 2)
            if len(parts) >= 2:
                frontmatter = yaml.safe_load(parts[1])
                return frontmatter.get("title", "Untitled")
        except Exception:
            pass
        return "Untitled"

    async def list_topics(self) -> list[str]:
        if not self.knowledge_dir.exists():
            return []
        return [
            d.name for d in self.knowledge_dir.iterdir()
            if d.is_dir() and d.name != ".git"
        ]
