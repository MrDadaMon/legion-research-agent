from __future__ import annotations
import numpy as np
import sqlite_vec
from sentence_transformers import SentenceTransformer
from typing import AsyncIterator

# Constants from 03-RESEARCH.md
EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2 produces 384-dim vectors
SIMILARITY_THRESHOLD = 0.85
DISTANCE_THRESHOLD = 1 - SIMILARITY_THRESHOLD  # 0.15

# Singleton model instance
_model = None

def get_embedding_model() -> SentenceTransformer:
    """Get or create the singleton embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def generate_content_embedding(title: str, content: str) -> list[float]:
    """Generate embedding for content using title + first 500 chars of content.

    Returns a list of floats (384-dimensional).
    """
    model = get_embedding_model()
    text = f"{title}. {content[:500]}"
    embedding = model.encode(text)
    return embedding.tolist()


class EmbeddingStore:
    """Handles sqlite-vec extension for vector storage and similarity queries.

    Usage:
        store = EmbeddingStore(db_path="knowledge/legion.db")
        await store.initialize()  # Creates vec0 virtual table if needed
        await store.insert_embedding(content_id, embedding)
        similar = await store.find_similar_on_topic(topic_slug, embedding, content_id)
    """

    def __init__(self, db_path: str = "knowledge/legion.db"):
        self.db_path = db_path
        self._conn = None

    async def connect(self) -> None:
        """Connect to database and load sqlite-vec extension."""
        import aiosqlite
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA enable_load_extension")
            sqlite_vec.load(self._conn)
            await self._conn.execute("PRAGMA disable_load_extension")

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def initialize(self) -> None:
        """Create vec0 virtual table for content embeddings if it doesn't exist."""
        await self.connect()

        # Check if table exists
        cursor = await self._conn.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='content_embeddings'
        """)
        row = await cursor.fetchone()

        if row is None:
            # Create virtual table with exact dimension for all-MiniLM-L6-v2
            await self._conn.execute(f"""
                CREATE VIRTUAL TABLE content_embeddings USING vec0(
                    content_id INTEGER,
                    embedding FLOAT[{EMBEDDING_DIMENSION}]
                )
            """)
            await self._conn.commit()
            print("Created content_embeddings virtual table with dimension", EMBEDDING_DIMENSION)

    async def insert_embedding(self, content_id: int, embedding: list[float]) -> None:
        """Insert or replace embedding for a content item."""
        await self.connect()

        # Serialize as float32 array
        embedding_np = np.array(embedding, dtype=np.float32)

        # Delete existing if present
        await self._conn.execute(
            "DELETE FROM content_embeddings WHERE content_id = ?",
            (content_id,)
        )

        # Insert new
        await self._conn.execute(
            "INSERT INTO content_embeddings (content_id, embedding) VALUES (?, ?)",
            (content_id, embedding_np)
        )
        await self._conn.commit()

    async def find_similar_on_topic(
        self,
        topic_slug: str,
        embedding: list[float],
        exclude_content_id: int | None = None,
        limit: int = 5
    ) -> list[dict]:
        """Find content similar to given embedding on same topic.

        Returns list of dicts: {content_id, title, distance}
        where distance < DISTANCE_THRESHOLD (0.15 = 85% similarity).
        """
        await self.connect()

        embedding_np = np.array(embedding, dtype=np.float32)

        query = """
            SELECT
                c.id as content_id,
                c.title,
                vec_distance_cosine(ce.embedding, ?) as distance
            FROM content_embeddings ce
            JOIN content c ON c.id = ce.content_id
            JOIN content_topics ct ON ct.content_id = c.id
            JOIN topics t ON t.id = ct.topic_id
            WHERE t.slug = ?
              AND ce.content_id != ?
              AND vec_distance_cosine(ce.embedding, ?) < ?
            ORDER BY distance
            LIMIT ?
        """

        cursor = await self._conn.execute(query, [
            embedding_np,
            topic_slug,
            exclude_content_id if exclude_content_id else 0,
            embedding_np,
            DISTANCE_THRESHOLD,
            limit
        ])

        rows = await cursor.fetchall()
        return [
            {
                'content_id': row['content_id'],
                'title': row['title'],
                'distance': row['distance']
            }
            for row in rows
        ]

    async def get_embedding(self, content_id: int) -> list[float] | None:
        """Get embedding for a content item. Returns None if not found."""
        await self.connect()

        cursor = await self._conn.execute(
            "SELECT embedding FROM content_embeddings WHERE content_id = ?",
            (content_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        # Deserialize - sqlite-vec returns numpy array
        embedding = row['embedding']
        if hasattr(embedding, 'tolist'):
            return embedding.tolist()
        return list(embedding)