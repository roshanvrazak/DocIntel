"""
Load and concurrency tests.

These tests verify that the API handles parallel requests correctly without
race conditions, data corruption, or crashes. All external I/O is mocked.
"""
import asyncio
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from backend.app.main import app

VALID_PDF = b"%PDF-1.4 load test pdf"


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Upload concurrency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("backend.app.api.routes.upload.process_document")
@patch("backend.app.api.routes.upload.get_session")
async def test_parallel_uploads(mock_get_session, mock_task):
    """10 simultaneous uploads should all succeed independently."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_get_session.return_value = mock_db
    mock_task.delay = MagicMock()

    async def single_upload(client: AsyncClient, index: int):
        return await client.post(
            "/api/upload",
            files=[("file", (f"doc_{index}.pdf", io.BytesIO(VALID_PDF), "application/pdf"))],
        )

    async with await _client() as client:
        responses = await asyncio.gather(
            *[single_upload(client, i) for i in range(10)]
        )

    statuses = [r.status_code for r in responses]
    assert all(s == 200 for s in statuses), f"Some uploads failed: {statuses}"

    ids = [r.json()["id"] for r in responses]
    assert len(set(ids)) == 10, "Each upload should produce a unique document ID"


@pytest.mark.asyncio
@patch("backend.app.api.routes.upload.process_document")
@patch("backend.app.api.routes.upload.get_session")
async def test_parallel_uploads_produce_unique_ids(mock_get_session, mock_task):
    """Document IDs must be unique across concurrent requests."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_get_session.return_value = mock_db
    mock_task.delay = MagicMock()

    async with await _client() as client:
        responses = await asyncio.gather(
            *[
                client.post(
                    "/api/upload",
                    files=[("file", ("doc.pdf", io.BytesIO(VALID_PDF), "application/pdf"))],
                )
                for _ in range(5)
            ]
        )

    ids = [r.json()["id"] for r in responses if r.status_code == 200]
    assert len(ids) == len(set(ids)), "Duplicate doc IDs detected under concurrent load"


# ---------------------------------------------------------------------------
# Chat concurrency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("backend.app.api.routes.chat.graph")
async def test_concurrent_chat_queries(mock_graph):
    """20 simultaneous chat queries should all complete without errors."""
    mock_graph.ainvoke = AsyncMock(
        return_value={"final_response": "Concurrent response."}
    )

    async def single_query(client: AsyncClient, i: int):
        return await client.post(
            "/api/chat",
            json={"query": f"Question number {i}?", "action": "qa", "doc_ids": []},
        )

    async with await _client() as client:
        responses = await asyncio.gather(
            *[single_query(client, i) for i in range(20)]
        )

    statuses = [r.status_code for r in responses]
    assert all(s == 200 for s in statuses), f"Some queries failed: {statuses}"


@pytest.mark.asyncio
@patch("backend.app.api.routes.chat.graph")
@patch("backend.app.api.routes.upload.process_document")
@patch("backend.app.api.routes.upload.get_session")
async def test_upload_and_chat_concurrently(mock_get_session, mock_task, mock_graph):
    """Simultaneous uploads and chat queries must not interfere with each other."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_get_session.return_value = mock_db
    mock_task.delay = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"final_response": "Answer."})

    async with await _client() as client:
        upload_tasks = [
            client.post(
                "/api/upload",
                files=[("file", (f"doc_{i}.pdf", io.BytesIO(VALID_PDF), "application/pdf"))],
            )
            for i in range(5)
        ]
        chat_tasks = [
            client.post(
                "/api/chat",
                json={"query": f"Query {i}?", "action": "qa", "doc_ids": []},
            )
            for i in range(5)
        ]
        all_responses = await asyncio.gather(*upload_tasks, *chat_tasks)

    assert all(r.status_code == 200 for r in all_responses)
