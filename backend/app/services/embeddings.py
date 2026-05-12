"""Embedding service for semantic search using pgvector + sentence-transformers.

Uses paraphrase-multilingual-MiniLM-L12-v2 (384 dimensions) for Spanish text.
Requires pgvector extension enabled in PostgreSQL.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_EMBEDDING_DIM = 384
_model = None


def _get_model():
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(_MODEL_NAME)
            logger.info("Loaded embedding model: %s (dim=%d)", _MODEL_NAME, _EMBEDDING_DIM)
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise
    return _model


def embed_text(text_input: str) -> list[float]:
    """Generate embedding vector for a single text."""
    model = _get_model()
    embedding = model.encode(text_input, normalize_embeddings=True)
    return embedding.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for a batch of texts."""
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return embeddings.tolist()


async def ensure_embedding_column(db: AsyncSession) -> None:
    """Add embedding column to social_posts if it doesn't exist.

    Uses raw SQL since Alembic migrations may not be run yet.
    """
    await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await db.execute(
        text(f"""
        ALTER TABLE social_posts
        ADD COLUMN IF NOT EXISTS embedding vector({_EMBEDDING_DIM})
    """)
    )
    # Create HNSW index for fast similarity search
    await db.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_social_posts_embedding
        ON social_posts
        USING hnsw (embedding vector_cosine_ops)
    """)
    )
    await db.commit()
    logger.info("Embedding column and HNSW index ensured on social_posts")


async def backfill_embeddings(db: AsyncSession, batch_size: int = 100) -> int:
    """Generate embeddings for posts that don't have one yet."""
    result = await db.execute(
        text("""
        SELECT id, content FROM social_posts
        WHERE embedding IS NULL AND content IS NOT NULL AND content != ''
        LIMIT :batch_size
    """),
        {"batch_size": batch_size},
    )
    rows = result.fetchall()

    if not rows:
        return 0

    ids = [r[0] for r in rows]
    texts = [r[1] for r in rows]
    embeddings = embed_batch(texts)

    for post_id, emb in zip(ids, embeddings, strict=False):
        await db.execute(
            text("UPDATE social_posts SET embedding = :emb WHERE id = :id"),
            {"emb": str(emb), "id": post_id},
        )

    await db.commit()
    logger.info("Backfilled %d embeddings", len(ids))
    return len(ids)


async def search_similar_posts(
    db: AsyncSession,
    query: str,
    *,
    org_id: int,
    limit: int = 10,
    min_similarity: float = 0.3,
) -> list[dict[str, Any]]:
    """Find posts semantically similar to the query text, scoped to one org.

    S4.8 — Multi-tenant safety: `org_id` is REQUIRED (kw-only) so callers
    cannot accidentally omit it. The query JOINs through
    `social_profiles` → `dirigentes` and filters by `dirigentes.org_id`
    before the HNSW ORDER BY. The planner may choose post-filter
    (HNSW top-N then filter) or pre-filter (btree on dirigentes.org_id
    then sequential) — BOTH are correct for isolation; we only care that
    cross-org leak is impossible.

    NOTE: `social_posts` has no direct `org_id` column — multi-tenancy is
    mediated by the profile→dirigente→org chain. RLS on `social_posts`
    would require adding that column first (future work).
    """
    query_embedding = embed_text(query)

    # The JOIN ensures every row returned belongs to a dirigente of the
    # caller's org. We use `similarity > min_sim` in WHERE so pgvector can
    # still leverage the HNSW index via the ORDER BY clause.
    result = await db.execute(
        text("""
        SELECT
            sp.id,
            sp.content,
            sp.platform_post_id,
            sp.profile_id,
            sp.likes,
            sp.comments,
            sp.published_at,
            1 - (sp.embedding <=> cast(:query_emb AS vector)) AS similarity
        FROM social_posts sp
        JOIN social_profiles prof ON prof.id = sp.profile_id
        JOIN dirigentes d ON d.id = prof.dirigente_id
        WHERE d.org_id = :org_id
          AND sp.embedding IS NOT NULL
          AND 1 - (sp.embedding <=> cast(:query_emb AS vector)) > :min_sim
        ORDER BY sp.embedding <=> cast(:query_emb AS vector)
        LIMIT :limit
    """),
        {
            "query_emb": str(query_embedding),
            "org_id": org_id,
            "min_sim": min_similarity,
            "limit": limit,
        },
    )

    return [
        {
            "id": row[0],
            "content": row[1],
            "platform_post_id": row[2],
            "profile_id": row[3],
            "likes": row[4],
            "comments": row[5],
            "published_at": row[6],
            "similarity": round(float(row[7]), 4),
        }
        for row in result.fetchall()
    ]
