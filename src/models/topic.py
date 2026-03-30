from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class Topic:
    id: int | None
    name: str
    slug: str
    created_at: str


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug
