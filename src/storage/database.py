import aiosqlite
import re
from datetime import datetime
import sqlite_vec

from src.models import ContentItem, Topic, compute_content_hash, slugify


class Database:
    def __init__(self, db_path: str = "knowledge/legion.db"):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def _ensure_connection(self):
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._init_db()

    async def _init_db(self):
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA busy_timeout=5000")
        await self._conn.execute("PRAGMA foreign_keys=ON")

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_url TEXT,
                title TEXT NOT NULL,
                raw_content TEXT NOT NULL,
                processed_date TEXT NOT NULL,
                content_hash TEXT UNIQUE NOT NULL,
                reference_count INTEGER DEFAULT 1
            )
        """)

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                slug TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """)

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS content_topics (
                content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
                topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
                PRIMARY KEY (content_id, topic_id)
            )
        """)

        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_hash ON content(content_hash)"
        )

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                preference_type TEXT NOT NULL CHECK(preference_type IN ('prefer', 'reject')),
                approach TEXT NOT NULL,
                reason TEXT,
                source_content_id INTEGER REFERENCES content(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_preferences_topic ON preferences(topic)")
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_preferences_type ON preferences(preference_type)")

        await self._conn.commit()

        # topic_metadata table for gap detection (GAP-01)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_metadata (
                topic_id INTEGER PRIMARY KEY REFERENCES topics(id) ON DELETE CASCADE,
                last_content_date TEXT NOT NULL,
                content_count INTEGER NOT NULL DEFAULT 0,
                last_gap_suggestion TEXT
            )
        """)

        # conflict_records table to track resolved conflicts
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS conflict_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                content_a_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
                content_b_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
                disagreement_summary TEXT NOT NULL,
                resolution TEXT CHECK(resolution IN ('a_preferred', 'b_preferred', 'both_kept')),
                resolved_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # research_sessions table for session logging (Phase 08)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS research_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                query TEXT NOT NULL,
                seed_content_id INTEGER REFERENCES content(id) ON DELETE SET NULL,
                results_count INTEGER DEFAULT 0,
                deliverable_types TEXT,
                notes TEXT
            )
        """)

        await self._conn.commit()

    async def insert_content(self, item: ContentItem) -> int:
        await self._ensure_connection()
        cursor = await self._conn.execute(
            """
            INSERT OR IGNORE INTO content
                (source_type, source_url, title, raw_content, processed_date, content_hash, reference_count)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                item.source_type,
                item.source_url,
                item.title,
                item.raw_content,
                item.processed_date,
                item.content_hash,
            ),
        )
        await self._conn.commit()

        if cursor.rowcount == 0:
            await self._conn.execute(
                """
                UPDATE content SET reference_count = reference_count + 1
                WHERE content_hash = ?
                """,
                (item.content_hash,),
            )
            await self._conn.commit()

        cursor = await self._conn.execute(
            "SELECT id FROM content WHERE content_hash = ?", (item.content_hash,)
        )
        row = await cursor.fetchone()
        return row["id"]

    async def get_content(self, content_id: int) -> ContentItem | None:
        await self._ensure_connection()
        cursor = await self._conn.execute(
            "SELECT * FROM content WHERE id = ?", (content_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return ContentItem(
            id=row["id"],
            source_type=row["source_type"],
            source_url=row["source_url"],
            title=row["title"],
            raw_content=row["raw_content"],
            processed_date=row["processed_date"],
            content_hash=row["content_hash"],
            reference_count=row["reference_count"],
        )

    async def get_all_content(self) -> list[ContentItem]:
        await self._ensure_connection()
        cursor = await self._conn.execute("SELECT * FROM content ORDER BY id")
        rows = await cursor.fetchall()
        return [
            ContentItem(
                id=row["id"],
                source_type=row["source_type"],
                source_url=row["source_url"],
                title=row["title"],
                raw_content=row["raw_content"],
                processed_date=row["processed_date"],
                content_hash=row["content_hash"],
                reference_count=row["reference_count"],
            )
            for row in rows
        ]

    async def content_exists_by_hash(self, content_hash: str) -> bool:
        await self._ensure_connection()
        cursor = await self._conn.execute(
            "SELECT 1 FROM content WHERE content_hash = ? LIMIT 1",
            (content_hash,),
        )
        row = await cursor.fetchone()
        return row is not None

    async def get_or_create_topic(self, name: str) -> tuple[int, str]:
        await self._ensure_connection()
        topic_slug = slugify(name)
        created_at = datetime.now().isoformat()

        await self._conn.execute(
            """
            INSERT OR IGNORE INTO topics (name, slug, created_at)
            VALUES (?, ?, ?)
            """,
            (name, topic_slug, created_at),
        )
        await self._conn.commit()

        cursor = await self._conn.execute(
            "SELECT id FROM topics WHERE slug = ?", (topic_slug,)
        )
        row = await cursor.fetchone()
        return row["id"], topic_slug

    async def link_content_to_topic(self, content_id: int, topic_id: int) -> None:
        await self._ensure_connection()
        await self._conn.execute(
            """
            INSERT OR IGNORE INTO content_topics (content_id, topic_id)
            VALUES (?, ?)
            """,
            (content_id, topic_id),
        )
        await self._conn.commit()

    async def get_content_topics(self, content_id: int) -> list[str]:
        await self._ensure_connection()
        cursor = await self._conn.execute(
            """
            SELECT t.slug FROM topics t
            JOIN content_topics ct ON ct.topic_id = t.id
            WHERE ct.content_id = ?
            """,
            (content_id,),
        )
        rows = await cursor.fetchall()
        return [row["slug"] for row in rows]

    async def get_topic_content(self, topic_slug: str) -> list[ContentItem]:
        await self._ensure_connection()
        cursor = await self._conn.execute(
            """
            SELECT c.* FROM content c
            JOIN content_topics ct ON ct.content_id = c.id
            JOIN topics t ON t.id = ct.topic_id
            WHERE t.slug = ?
            ORDER BY c.id
            """,
            (topic_slug,),
        )
        rows = await cursor.fetchall()
        return [
            ContentItem(
                id=row["id"],
                source_type=row["source_type"],
                source_url=row["source_url"],
                title=row["title"],
                raw_content=row["raw_content"],
                processed_date=row["processed_date"],
                content_hash=row["content_hash"],
                reference_count=row["reference_count"],
            )
            for row in rows
        ]

    async def insert_preference(
        self,
        topic: str,
        preference_type: str,
        approach: str,
        reason: str | None = None,
        source_content_id: int | None = None
    ) -> int:
        """Insert a preference or rejection. Returns the row id."""
        await self._ensure_connection()
        cursor = await self._conn.execute("""
            INSERT INTO preferences (topic, preference_type, approach, reason, source_content_id, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (topic, preference_type, approach, reason, source_content_id))
        await self._conn.commit()
        return cursor.lastrowid

    async def get_preferences(self, topic: str | None = None, preference_type: str | None = None) -> list[dict]:
        """Get preferences, optionally filtered by topic and/or type."""
        await self._ensure_connection()
        query = "SELECT * FROM preferences WHERE 1=1"
        params = []
        if topic:
            query += " AND topic = ?"
            params.append(topic)
        if preference_type:
            query += " AND preference_type = ?"
            params.append(preference_type)
        query += " ORDER BY created_at DESC"
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_rejections(self, topic: str | None = None) -> list[dict]:
        """Get all rejections, optionally filtered by topic."""
        return await self.get_preferences(topic=topic, preference_type='reject')

    async def check_rejection_match(self, user_message: str) -> list[dict]:
        """Check if user message mentions any rejected approaches. Returns list of {approach, reason, topic}."""
        import re
        await self._ensure_connection()
        cursor = await self._conn.execute(
            "SELECT topic, approach, reason FROM preferences WHERE preference_type = 'reject'"
        )
        rejections = await cursor.fetchall()
        user_lower = user_message.lower()
        matches = []
        for rejection in rejections:
            pattern = r'\b' + re.escape(rejection['approach'].lower()) + r'\b'
            if re.search(pattern, user_lower):
                matches.append({
                    'topic': rejection['topic'],
                    'approach': rejection['approach'],
                    'reason': rejection['reason']
                })
        return matches

    async def update_topic_metadata(self, topic_id: int) -> bool:
        """Update topic metadata when new content is added. Returns True if gap should be suggested."""
        await self._ensure_connection()
        now = datetime.now().isoformat()

        cursor = await self._conn.execute(
            "SELECT content_count, last_content_date FROM topic_metadata WHERE topic_id = ?",
            (topic_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            await self._conn.execute(
                "INSERT INTO topic_metadata (topic_id, last_content_date, content_count) VALUES (?, ?, 1)",
                (topic_id, now)
            )
        else:
            await self._conn.execute("""
                UPDATE topic_metadata
                SET last_content_date = ?, content_count = content_count + 1
                WHERE topic_id = ?
            """, (now, topic_id))

        await self._conn.commit()
        return False  # Gap suggestion handled by gap_handler

    async def get_topic_metadata(self, topic_id: int) -> dict | None:
        """Get metadata for a topic."""
        await self._ensure_connection()
        cursor = await self._conn.execute(
            "SELECT * FROM topic_metadata WHERE topic_id = ?",
            (topic_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def record_conflict(
        self,
        topic: str,
        content_a_id: int,
        content_b_id: int,
        disagreement_summary: str,
        resolution: str | None = None
    ) -> int:
        """Record a conflict between two content pieces. Returns conflict id."""
        await self._ensure_connection()
        cursor = await self._conn.execute("""
            INSERT INTO conflict_records (topic, content_a_id, content_b_id, disagreement_summary, resolution)
            VALUES (?, ?, ?, ?, ?)
        """, (topic, content_a_id, content_b_id, disagreement_summary, resolution))
        await self._conn.commit()
        return cursor.lastrowid

    async def resolve_conflict_record(self, conflict_id: int, resolution: str) -> None:
        """Update conflict record with resolution."""
        await self._ensure_connection()
        await self._conn.execute("""
            UPDATE conflict_records
            SET resolution = ?, resolved_at = datetime('now')
            WHERE id = ?
        """, (resolution, conflict_id))
        await self._conn.commit()

    async def insert_research_session(
        self,
        query: str,
        seed_content_id: int | None = None,
        results_count: int = 0,
        deliverable_types: str | None = None,
        notes: str | None = None,
    ) -> int:
        """Insert a research session log entry. Returns the session id."""
        await self._ensure_connection()
        cursor = await self._conn.execute(
            """
            INSERT INTO research_sessions
                (query, seed_content_id, results_count, deliverable_types, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (query, seed_content_id, results_count, deliverable_types, notes),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def update_research_session(
        self,
        session_id: int,
        results_count: int | None = None,
        deliverable_types: str | None = None,
        notes: str | None = None,
    ) -> None:
        """Update a research session with results info."""
        await self._ensure_connection()
        if results_count is not None:
            await self._conn.execute(
                "UPDATE research_sessions SET results_count = ? WHERE id = ?",
                (results_count, session_id),
            )
        if deliverable_types is not None:
            await self._conn.execute(
                "UPDATE research_sessions SET deliverable_types = ? WHERE id = ?",
                (deliverable_types, session_id),
            )
        if notes is not None:
            await self._conn.execute(
                "UPDATE research_sessions SET notes = ? WHERE id = ?",
                (notes, session_id),
            )
        await self._conn.commit()

    async def get_recent_sessions(self, limit: int = 10) -> list[dict]:
        """Get the most recent research sessions."""
        await self._ensure_connection()
        cursor = await self._conn.execute(
            """
            SELECT rs.*, c.title as seed_content_title
            FROM research_sessions rs
            LEFT JOIN content c ON c.id = rs.seed_content_id
            ORDER BY rs.timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_session_history(
        self,
        topic: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Get research session history, optionally filtered by topic keyword."""
        await self._ensure_connection()
        if topic:
            cursor = await self._conn.execute(
                """
                SELECT rs.*, c.title as seed_content_title
                FROM research_sessions rs
                LEFT JOIN content c ON c.id = rs.seed_content_id
                WHERE rs.query LIKE ?
                ORDER BY rs.timestamp DESC
                LIMIT ?
                """,
                (f"%{topic}%", limit),
            )
        else:
            cursor = await self._conn.execute(
                """
                SELECT rs.*, c.title as seed_content_title
                FROM research_sessions rs
                LEFT JOIN content c ON c.id = rs.seed_content_id
                ORDER BY rs.timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None
