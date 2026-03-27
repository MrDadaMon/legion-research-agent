from datetime import datetime

from src.models import ContentItem, compute_content_hash
from src.pipeline import detect_content_type
from src.pipeline.extractors import (
    extract_youtube,
    scrape_article,
    extract_pdf,
    classify_and_store,
)
from src.storage.sync_manager import SyncManager


async def process_content(
    input_str: str, sync_manager: SyncManager, topic: str = "general"
) -> ContentItem:
    content_type = detect_content_type(input_str)

    if content_type == "youtube":
        title, raw_content, _ = await extract_youtube(input_str)
    elif content_type == "article":
        title, raw_content = await scrape_article(input_str)
    elif content_type == "pdf":
        title, raw_content = await extract_pdf(input_str)
    else:
        _, title, raw_content = await classify_and_store(input_str)

    source_url = input_str if content_type in ("youtube", "article", "pdf") else None

    item = ContentItem(
        id=None,
        source_type=content_type,
        source_url=source_url,
        title=title,
        raw_content=raw_content,
        processed_date=datetime.now().isoformat(),
        content_hash=compute_content_hash(raw_content),
        reference_count=1,
    )

    content_id = await sync_manager.write_content(item, topic)
    item.id = content_id
    return item
