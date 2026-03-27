from src.storage.database import Database
from src.storage.markdown_store import MarkdownStore
from src.models import ContentItem


class SyncManager:
    def __init__(self, db: Database, markdown_store: MarkdownStore):
        self.db = db
        self.markdown_store = markdown_store

    async def write_content(self, item: ContentItem, topic_name: str = "general") -> int:
        content_id = await self.db.insert_content(item)
        item.id = content_id

        topic_id, topic_slug = await self.db.get_or_create_topic(topic_name)
        await self.db.link_content_to_topic(content_id, topic_id)

        await self.markdown_store.save(item, topic_slug)
        return content_id

    async def reconcile(self) -> dict[str, int]:
        missing_markdown = 0
        missing_sqlite = 0

        all_content = await self.db.get_all_content()
        for item in all_content:
            topics = await self.db.get_content_topics(item.id)
            if topics:
                topic_slug = topics[0]
            else:
                topic_slug = "general"

            md_exists = await self.markdown_store.load(topic_slug, item.id)
            if md_exists is None:
                missing_markdown += 1

        all_topics = await self.markdown_store.list_topics()
        for topic_slug in all_topics:
            topic_content = await self.markdown_store.list_topic_content(topic_slug)
            for content_id, title in topic_content:
                content = await self.db.get_content(content_id)
                if content is None:
                    missing_sqlite += 1

        return {
            "missing_markdown": missing_markdown,
            "missing_sqlite": missing_sqlite,
        }
