"""Tests for telephony tools — TransferTool, HangupTool, VoicemailTool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai_engine.tools.telephony.hangup import HangupTool
from ai_engine.tools.telephony.transfer import TransferTool
from ai_engine.tools.telephony.voicemail import VoicemailTool


def _mock_httpx_client(post_response):
    """Create a mock httpx.AsyncClient context manager."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=post_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _mock_response():
    """Create a mock httpx.Response (sync methods)."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    return resp


class TestTransferTool:
    def test_definition(self):
        t = TransferTool()
        d = t.definition
        assert d.name == "transfer"
        assert d.category.value == "telephony"
        param_names = [p.name for p in d.parameters]
        assert "target" in param_names
        assert "reason" in param_names

    @pytest.mark.asyncio
    async def test_execute_success(self, make_tool_context):
        ctx = make_tool_context()
        mock_resp = _mock_response()
        mock_client = _mock_httpx_client(mock_resp)

        with patch(
            "ai_engine.tools.telephony.transfer.httpx.AsyncClient", return_value=mock_client
        ):
            result = await TransferTool().execute({"target": "1001"}, ctx)

        assert result["success"] is True
        assert result["target"] == "1001"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/transfer" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_execute_no_target(self, make_tool_context):
        ctx = make_tool_context()
        result = await TransferTool().execute({}, ctx)
        assert result["success"] is False
        assert "No transfer target" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_http_error(self, make_tool_context):
        ctx = make_tool_context()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "ai_engine.tools.telephony.transfer.httpx.AsyncClient", return_value=mock_client
        ):
            result = await TransferTool().execute({"target": "1001"}, ctx)

        assert result["success"] is False
        assert "Transfer failed" in result["error"]


class TestHangupTool:
    def test_definition(self):
        t = HangupTool()
        d = t.definition
        assert d.name == "hangup"
        assert d.category.value == "telephony"

    @pytest.mark.asyncio
    async def test_execute_success(self, make_tool_context):
        ctx = make_tool_context()
        mock_resp = _mock_response()
        mock_client = _mock_httpx_client(mock_resp)

        with patch("ai_engine.tools.telephony.hangup.httpx.AsyncClient", return_value=mock_client):
            result = await HangupTool().execute({}, ctx)

        assert result["success"] is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/hangup" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_execute_http_error(self, make_tool_context):
        ctx = make_tool_context()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("ai_engine.tools.telephony.hangup.httpx.AsyncClient", return_value=mock_client):
            result = await HangupTool().execute({}, ctx)

        assert result["success"] is False
        assert "Hangup failed" in result["error"]


class TestVoicemailTool:
    def test_definition(self):
        t = VoicemailTool()
        d = t.definition
        assert d.name == "voicemail"
        assert d.category.value == "telephony"
        param_names = [p.name for p in d.parameters]
        assert "extension" in param_names

    @pytest.mark.asyncio
    async def test_execute_success(self, make_tool_context):
        ctx = make_tool_context()
        mock_resp = _mock_response()
        mock_client = _mock_httpx_client(mock_resp)

        with patch(
            "ai_engine.tools.telephony.voicemail.httpx.AsyncClient", return_value=mock_client
        ):
            result = await VoicemailTool().execute({"extension": "1001"}, ctx)

        assert result["success"] is True
        assert result["extension"] == "1001"
        # Should prefix with *97
        call_json = mock_client.post.call_args[1]["json"]
        assert call_json["target"] == "*971001"

    @pytest.mark.asyncio
    async def test_execute_no_extension(self, make_tool_context):
        ctx = make_tool_context()
        result = await VoicemailTool().execute({}, ctx)
        assert result["success"] is False
        assert "No extension" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_http_error(self, make_tool_context):
        ctx = make_tool_context()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "ai_engine.tools.telephony.voicemail.httpx.AsyncClient", return_value=mock_client
        ):
            result = await VoicemailTool().execute({"extension": "1001"}, ctx)

        assert result["success"] is False
        assert "Voicemail transfer failed" in result["error"]
