from __future__ import annotations
import aiosqlite
from typing import NamedTuple


class Backlink(NamedTuple):
    source_id: int
    link_text: str
    context: str | None


class BacklinksIndex:
    def __init__(self, db_path: str = "knowledge/legion.db"):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def _ensure_connection(self):
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            await self._init_db()

    async def _init_db(self):
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS backlinks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                link_text TEXT NOT NULL,
                context TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (source_id) REFERENCES content(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES content(id) ON DELETE CASCADE,
                UNIQUE(source_id, target_id, link_text)
            )
        """)
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_backlinks_target ON backlinks(target_id)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_backlinks_source ON backlinks(source_id)"
        )
        await self._conn.commit()

    async def add_backlink(
        self,
        source_id: int,
        target_id: int,
        link_text: str,
        context: str | None = None,
    ) -> int:
        """Add a backlink from source_id to target_id. Returns backlink id."""
        await self._ensure_connection()
        cursor = await self._conn.execute(
            """
            INSERT OR IGNORE INTO backlinks (source_id, target_id, link_text, context)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, target_id, link_text, context),
        )
        await self._conn.commit()
        return cursor.lastrowid or 0

    async def get_backlinks(self, target_id: int) -> list[Backlink]:
        """Get all content that links TO the given content item."""
        await self._ensure_connection()
        cursor = await self._conn.execute(
            """
            SELECT source_id, link_text, context
            FROM backlinks
            WHERE target_id = ?
            ORDER BY created_at DESC
            """,
            (target_id,),
        )
        rows = await cursor.fetchall()
        return [Backlink(source_id=r[0], link_text=r[1], context=r[2]) for r in rows]

    async def get_outgoing_links(self, source_id: int) -> list[tuple[int, str]]:
        """Get all content this item links TO."""
        await self._ensure_connection()
        cursor = await self._conn.execute(
            """
            SELECT target_id, link_text
            FROM backlinks
            WHERE source_id = ?
            """,
            (source_id,),
        )
        rows = await cursor.fetchall()
        return [(r[0], r[1]) for r in rows]

    async def remove_backlinks_for_content(self, content_id: int) -> None:
        """Remove all backlinks (incoming and outgoing) for a content item."""
        await self._ensure_connection()
        await self._conn.execute(
            "DELETE FROM backlinks WHERE source_id = ? OR target_id = ?",
            (content_id, content_id),
        )
        await self._conn.commit()

    async def get_linked_content_ids(self, content_id: int) -> list[int]:
        """Get all content IDs that are linked from or link to this content."""
        await self._ensure_connection()
        cursor = await self._conn.execute(
            """
            SELECT DISTINCT target_id FROM backlinks WHERE source_id = ?
            UNION
            SELECT DISTINCT source_id FROM backlinks WHERE target_id = ?
            """,
            (content_id, content_id),
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None
