"""Tests for ai_engine.api.router — all 5 endpoints via TestClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai_engine.core.models import CallSession
from ai_engine.main import create_app


@pytest.fixture()
def app():
    return create_app()


@pytest.fixture()
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "ai-engine"


class TestStartCall:
    @pytest.mark.asyncio
    async def test_start_success(self, client):
        with patch("ai_engine.api.router.engine") as mock_engine:
            mock_engine.start_call = AsyncMock()

            resp = await client.post(
                "/start",
                json={
                    "call_id": "c1",
                    "tenant_id": "t1",
                    "context_name": "ivr",
                    "provider_name": "openai_realtime",
                    "api_key": "sk-test",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["call_id"] == "c1"
        assert data["provider"] == "openai_realtime"

    @pytest.mark.asyncio
    async def test_start_no_provider(self, client):
        resp = await client.post(
            "/start",
            json={
                "call_id": "c1",
                "tenant_id": "t1",
                "context_name": "ivr",
                # No provider_name
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_start_pipeline_mode(self, client):
        with patch("ai_engine.api.router.engine") as mock_engine:
            mock_engine.start_call = AsyncMock()

            resp = await client.post(
                "/start",
                json={
                    "call_id": "c1",
                    "tenant_id": "t1",
                    "context_name": "ivr",
                    "provider_mode": "pipeline",
                    "api_key": "sk-test",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "pipeline"

    @pytest.mark.asyncio
    async def test_start_engine_error(self, client):
        with patch("ai_engine.api.router.engine") as mock_engine:
            mock_engine.start_call = AsyncMock(side_effect=RuntimeError("boom"))

            resp = await client.post(
                "/start",
                json={
                    "call_id": "c1",
                    "tenant_id": "t1",
                    "context_name": "ivr",
                    "provider_name": "openai_realtime",
                    "api_key": "sk-test",
                },
            )

        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_start_with_tools(self, client):
        with (
            patch("ai_engine.api.router.engine") as mock_engine,
            patch("ai_engine.api.router.tool_registry") as mock_registry,
        ):
            mock_engine.start_call = AsyncMock()
            mock_registry.to_openai_schemas.return_value = [
                {"type": "function", "function": {"name": "transfer"}}
            ]

            resp = await client.post(
                "/start",
                json={
                    "call_id": "c1",
                    "tenant_id": "t1",
                    "context_name": "ivr",
                    "provider_name": "openai_realtime",
                    "api_key": "sk-test",
                    "tools": ["transfer"],
                },
            )

        assert resp.status_code == 200
        mock_registry.to_openai_schemas.assert_called_once_with(["transfer"])

    @pytest.mark.asyncio
    async def test_start_missing_required(self, client):
        resp = await client.post("/start", json={"call_id": "c1"})
        assert resp.status_code == 422  # Pydantic validation error


class TestStopCall:
    @pytest.mark.asyncio
    async def test_stop_success(self, client):
        session = CallSession(
            call_id="c1", tenant_id="t1", context_name="ivr", provider_name="openai_realtime"
        )

        with (
            patch("ai_engine.api.router.engine") as mock_engine,
            patch("ai_engine.core.session_store.session_store") as mock_store,
        ):
            mock_store.get = AsyncMock(return_value=session)
            mock_engine.stop_call = AsyncMock()

            resp = await client.post("/stop", json={"call_id": "c1"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "stopped"
        assert data["call_id"] == "c1"

    @pytest.mark.asyncio
    async def test_stop_not_found(self, client):
        with patch("ai_engine.core.session_store.session_store") as mock_store:
            mock_store.get = AsyncMock(return_value=None)
            resp = await client.post("/stop", json={"call_id": "nonexistent"})

        assert resp.status_code == 404


class TestTestProvider:
    @pytest.mark.asyncio
    async def test_unknown_provider(self, client):
        resp = await client.post(
            "/test-provider",
            json={"provider_name": "nonexistent", "api_key": "sk-test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "Unknown provider" in data["error"]

    @pytest.mark.asyncio
    async def test_openai_success(self, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            resp = await client.post(
                "/test-provider",
                json={"provider_name": "openai_realtime", "api_key": "sk-test"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "latency_ms" in data

    @pytest.mark.asyncio
    async def test_http_error(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"

        mock_request = MagicMock()
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("401", request=mock_request, response=mock_resp)
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            resp = await client.post(
                "/test-provider",
                json={"provider_name": "openai_realtime", "api_key": "bad-key"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False


class TestTestContext:
    @pytest.mark.asyncio
    async def test_no_api_key(self, client):
        resp = await client.post(
            "/test-context",
            json={"system_prompt": "Be helpful.", "message": "Hello"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_provider(self, client):
        with patch(
            "ai_engine.pipelines.orchestrator.create_llm", side_effect=ValueError("Unknown LLM")
        ):
            resp = await client.post(
                "/test-context",
                json={
                    "system_prompt": "Be helpful.",
                    "message": "Hello",
                    "api_key": "sk-test",
                    "provider_name": "nonexistent",
                },
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_success(self, client):
        from ai_engine.pipelines.base import LLMChunk

        async def fake_generate(messages, tools=None, system_prompt=""):
            yield LLMChunk(text="Hello back!")

        mock_llm = AsyncMock()
        mock_llm.generate = fake_generate
        mock_llm.close = AsyncMock()

        with patch("ai_engine.pipelines.orchestrator.create_llm", return_value=mock_llm):
            resp = await client.post(
                "/test-context",
                json={
                    "system_prompt": "Be helpful.",
                    "message": "Hello",
                    "api_key": "sk-test",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["response"] == "Hello back!"
        assert "latency_ms" in data
