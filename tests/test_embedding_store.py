import pytest
from src.storage.embedding_store import (
    EmbeddingStore,
    generate_content_embedding,
    SIMILARITY_THRESHOLD,
    DISTANCE_THRESHOLD,
    EMBEDDING_DIMENSION,
)


class TestEmbeddingConstants:
    def test_embedding_dimension(self):
        """all-MiniLM-L6-v2 produces 384-dimensional vectors."""
        assert EMBEDDING_DIMENSION == 384

    def test_similarity_threshold(self):
        """Cosine similarity threshold is 0.85."""
        assert SIMILARITY_THRESHOLD == 0.85

    def test_distance_threshold(self):
        """Distance threshold is 0.15 (1 - 0.85)."""
        assert DISTANCE_THRESHOLD == pytest.approx(0.15)


class TestEmbeddingGeneration:
    def test_generate_content_embedding(self):
        """Embedding generation returns 384-dim list of floats."""
        embedding = generate_content_embedding(
            "Test Title",
            "This is test content for embedding generation."
        )

        assert isinstance(embedding, list)
        assert len(embedding) == EMBEDDING_DIMENSION
        assert all(isinstance(x, float) for x in embedding)

    def test_generate_embedding_consistent(self):
        """Same input produces same embedding."""
        embedding1 = generate_content_embedding("Same Title", "Same content")
        embedding2 = generate_content_embedding("Same Title", "Same content")

        # Should be very close (allow for tiny floating point differences)
        assert len(embedding1) == len(embedding2)
        diff = sum(abs(a - b) for a, b in zip(embedding1, embedding2))
        assert diff < 0.001, "Same input should produce nearly identical embeddings"

    def test_different_content_different_embedding(self):
        """Different content produces different embeddings."""
        embedding1 = generate_content_embedding("Title A", "Content about trading bots")
        embedding2 = generate_content_embedding("Title B", "Content about cooking recipes")

        # Should be noticeably different
        diff = sum(abs(a - b) for a, b in zip(embedding1, embedding2))
        assert diff > 0.5, "Different content should produce different embeddings"