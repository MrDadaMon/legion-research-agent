from __future__ import annotations
import hashlib
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContentItem:
    id: int | None
    source_type: str
    source_url: str | None
    title: str
    raw_content: str
    processed_date: str
    content_hash: str
    reference_count: int = 1


def compute_content_hash(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
