"""
Real pgvector integration tests.

These tests require a live PostgreSQL instance with pgvector installed.
Run only when DATABASE_URL points to a real test database:

    TEST_DATABASE_URL=postgresql://docintel:docintel@localhost:5432/docintel_test \
    pytest backend/tests/test_pgvector_integration.py -m integration -v

The `integration` mark is set on every test. CI skips these unless the
environment variable TEST_DATABASE_URL is present.
"""
import os
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Skip guard
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.skip(
        "TEST_DATABASE_URL not set — skipping pgvector integration tests",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Async DB fixtures (function-scoped so each test gets a clean session)
# ---------------------------------------------------------------------------

def _make_async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


@pytest_asyncio.fixture(scope="module")
async def db_engine():
    """Create engine and ensure schema/extensions exist."""
    async_url = _make_async_url(TEST_DATABASE_URL)
    engine = create_async_engine(async_url, echo=False)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Create tables from metadata
    from backend.app.db.base import Base
    from backend.app.models.document import Document, Chunk  # noqa: F401 — registers models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop test tables after the module finishes
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide a transactional session that rolls back after each test."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rand_embedding(dim: int = 768) -> list:
    """Return a deterministic-ish unit-ish vector for testing."""
    import math
    # Simple pattern: alternating 1/dim and -1/dim, normalised
    raw = [(1.0 if i % 2 == 0 else -1.0) / dim for i in range(dim)]
    mag = math.sqrt(sum(x * x for x in raw))
    return [x / mag for x in raw]


def _similar_embedding(dim: int = 768) -> list:
    """Return a vector very close to _rand_embedding (slightly perturbed)."""
    base = _rand_embedding(dim)
    import math
    perturbed = [x + (0.001 if i < 5 else 0.0) for i, x in enumerate(base)]
    mag = math.sqrt(sum(x * x for x in perturbed))
    return [x / mag for x in perturbed]


def _orthogonal_embedding(dim: int = 768) -> list:
    """Return a vector orthogonal (dissimilar) to _rand_embedding."""
    import math
    raw = [(1.0 if i % 3 == 0 else 0.0) / dim for i in range(dim)]
    mag = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / mag for x in raw]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insert_and_retrieve_chunk(db_session: AsyncSession):
    """Insert a Document + Chunk with embedding and retrieve it."""
    from backend.app.models.document import Document, Chunk

    doc = Document(filename="pgvector_test.pdf", status="ready")
    db_session.add(doc)
    await db_session.flush()

    chunk = Chunk(
        document_id=doc.id,
        content="The mitochondria is the powerhouse of the cell.",
        page_number=1,
        embedding=_rand_embedding(),
    )
    db_session.add(chunk)
    await db_session.flush()

    result = await db_session.execute(
        select(Chunk).where(Chunk.document_id == doc.id)
    )
    chunks = result.scalars().all()

    assert len(chunks) == 1
    assert chunks[0].content == "The mitochondria is the powerhouse of the cell."
    assert chunks[0].page_number == 1
    assert chunks[0].embedding is not None
    assert len(chunks[0].embedding) == 768


@pytest.mark.asyncio
async def test_cosine_similarity_orders_correctly(db_session: AsyncSession):
    """
    Insert two chunks: one similar to the query vector, one dissimilar.
    Dense search must return the similar chunk with a higher score.
    """
    from backend.app.models.document import Document, Chunk
    from backend.app.services.retriever import HybridRetriever

    doc = Document(filename="similarity_test.pdf", status="ready")
    db_session.add(doc)
    await db_session.flush()

    query_vec = _rand_embedding()
    similar_vec = _similar_embedding()
    dissimilar_vec = _orthogonal_embedding()

    close_chunk = Chunk(
        document_id=doc.id,
        content="This content is very relevant.",
        page_number=1,
        embedding=similar_vec,
    )
    far_chunk = Chunk(
        document_id=doc.id,
        content="This content is unrelated.",
        page_number=2,
        embedding=dissimilar_vec,
    )
    db_session.add_all([close_chunk, far_chunk])
    await db_session.flush()

    retriever = HybridRetriever(session=db_session)
    results = await retriever.dense_search(
        query_embedding=query_vec,
        top_k=2,
        document_ids=[doc.id],
    )

    assert len(results) == 2
    # The similar chunk should rank first (higher score)
    assert results[0]["chunk"].id == close_chunk.id
    assert results[0]["score"] > results[1]["score"]


@pytest.mark.asyncio
async def test_full_text_sparse_search(db_session: AsyncSession):
    """
    Insert two chunks with distinct keywords.
    Sparse search for one keyword should rank the matching chunk higher.
    """
    from backend.app.models.document import Document, Chunk
    from backend.app.services.retriever import HybridRetriever

    doc = Document(filename="sparse_test.pdf", status="ready")
    db_session.add(doc)
    await db_session.flush()

    mitochondria_chunk = Chunk(
        document_id=doc.id,
        content="The mitochondria produces ATP through oxidative phosphorylation.",
        page_number=1,
        embedding=_rand_embedding(),
    )
    photosynthesis_chunk = Chunk(
        document_id=doc.id,
        content="Chloroplasts perform photosynthesis converting light into energy.",
        page_number=2,
        embedding=_similar_embedding(),
    )
    db_session.add_all([mitochondria_chunk, photosynthesis_chunk])
    await db_session.flush()

    retriever = HybridRetriever(session=db_session)
    results = await retriever.sparse_search(
        query_text="mitochondria ATP",
        top_k=5,
        document_ids=[doc.id],
    )

    result_ids = [r["chunk"].id for r in results]
    assert mitochondria_chunk.id in result_ids
    # The mitochondria chunk must rank above (or equal to) the photosynthesis chunk
    mito_rank = result_ids.index(mitochondria_chunk.id)
    if photosynthesis_chunk.id in result_ids:
        photo_rank = result_ids.index(photosynthesis_chunk.id)
        assert mito_rank < photo_rank


@pytest.mark.asyncio
async def test_document_cascade_delete_removes_chunks(db_session: AsyncSession):
    """Deleting a Document must cascade-delete all its Chunks."""
    from backend.app.models.document import Document, Chunk

    doc = Document(filename="cascade_test.pdf", status="ready")
    db_session.add(doc)
    await db_session.flush()

    for i in range(3):
        db_session.add(Chunk(
            document_id=doc.id,
            content=f"Chunk number {i}",
            page_number=i + 1,
            embedding=_rand_embedding(),
        ))
    await db_session.flush()

    # Verify chunks exist
    result = await db_session.execute(
        select(Chunk).where(Chunk.document_id == doc.id)
    )
    assert len(result.scalars().all()) == 3

    # Delete document
    await db_session.delete(doc)
    await db_session.flush()

    # Chunks should be gone
    result = await db_session.execute(
        select(Chunk).where(Chunk.document_id == doc.id)
    )
    assert len(result.scalars().all()) == 0


@pytest.mark.asyncio
async def test_filter_by_document_id_in_dense_search(db_session: AsyncSession):
    """dense_search with document_ids filter must not return chunks from other docs."""
    from backend.app.models.document import Document, Chunk
    from backend.app.services.retriever import HybridRetriever

    doc_a = Document(filename="doc_a.pdf", status="ready")
    doc_b = Document(filename="doc_b.pdf", status="ready")
    db_session.add_all([doc_a, doc_b])
    await db_session.flush()

    query_vec = _rand_embedding()

    chunk_a = Chunk(document_id=doc_a.id, content="Document A content.", page_number=1, embedding=query_vec)
    chunk_b = Chunk(document_id=doc_b.id, content="Document B content.", page_number=1, embedding=query_vec)
    db_session.add_all([chunk_a, chunk_b])
    await db_session.flush()

    retriever = HybridRetriever(session=db_session)
    results = await retriever.dense_search(
        query_embedding=query_vec,
        top_k=10,
        document_ids=[doc_a.id],
    )

    result_doc_ids = {str(r["chunk"].document_id) for r in results}
    assert str(doc_a.id) in result_doc_ids
    assert str(doc_b.id) not in result_doc_ids
