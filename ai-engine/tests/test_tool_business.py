"""Tests for business tools — EmailSummaryTool, CreateTicketTool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai_engine.tools.business.create_ticket import CreateTicketTool
from ai_engine.tools.business.email_summary import EmailSummaryTool


def _mock_httpx_client(post_response):
    """Create a mock httpx.AsyncClient context manager."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=post_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _mock_response(json_data=None):
    """Create a mock httpx.Response (sync methods)."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
    return resp


class TestEmailSummaryTool:
    def test_definition(self):
        t = EmailSummaryTool()
        d = t.definition
        assert d.name == "email_summary"
        assert d.category.value == "business"
        param_names = [p.name for p in d.parameters]
        assert "to_email" in param_names
        assert "subject" in param_names
        assert "notes" in param_names

    @pytest.mark.asyncio
    async def test_execute_success(self, make_tool_context, make_session):
        session = make_session(caller_name="Alice", caller_number="+15551234567")
        session.add_transcript("caller", "I need help")
        session.add_transcript("agent", "Sure, how can I help?")
        ctx = make_tool_context(session=session)

        mock_resp = _mock_response()
        mock_client = _mock_httpx_client(mock_resp)

        with patch(
            "ai_engine.tools.business.email_summary.httpx.AsyncClient", return_value=mock_client
        ):
            result = await EmailSummaryTool().execute(
                {"to_email": "bob@example.com", "subject": "Call Summary"},
                ctx,
            )

        assert result["success"] is True
        call_json = mock_client.post.call_args[1]["json"]
        assert call_json["to"] == "bob@example.com"
        assert call_json["subject"] == "Call Summary"
        assert "Alice" in call_json["body"]
        assert "I need help" in call_json["body"]

    @pytest.mark.asyncio
    async def test_execute_no_email(self, make_tool_context):
        ctx = make_tool_context()
        result = await EmailSummaryTool().execute({}, ctx)
        assert result["success"] is False
        assert "No email" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_default_subject(self, make_tool_context, make_session):
        session = make_session(caller_name="Alice")
        ctx = make_tool_context(session=session)

        mock_resp = _mock_response()
        mock_client = _mock_httpx_client(mock_resp)

        with patch(
            "ai_engine.tools.business.email_summary.httpx.AsyncClient", return_value=mock_client
        ):
            result = await EmailSummaryTool().execute(
                {"to_email": "test@example.com"},
                ctx,
            )

        assert result["success"] is True
        call_json = mock_client.post.call_args[1]["json"]
        assert "Alice" in call_json["subject"]

    @pytest.mark.asyncio
    async def test_execute_http_error(self, make_tool_context):
        ctx = make_tool_context()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "ai_engine.tools.business.email_summary.httpx.AsyncClient", return_value=mock_client
        ):
            result = await EmailSummaryTool().execute(
                {"to_email": "test@example.com"},
                ctx,
            )

        assert result["success"] is False
        assert "Failed to send email" in result["error"]


class TestCreateTicketTool:
    def test_definition(self):
        t = CreateTicketTool()
        d = t.definition
        assert d.name == "create_ticket"
        assert d.category.value == "business"
        param_names = [p.name for p in d.parameters]
        assert "summary" in param_names
        assert "description" in param_names
        assert "priority" in param_names
        # Check enum on priority
        priority_param = next(p for p in d.parameters if p.name == "priority")
        assert priority_param.enum == ["low", "medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_execute_success(self, make_tool_context, make_session):
        session = make_session(caller_name="Bob", caller_number="+15559876543")
        ctx = make_tool_context(session=session, caller_name="Bob", caller_number="+15559876543")

        mock_resp = _mock_response(json_data={"ticket_id": "T-12345"})
        mock_client = _mock_httpx_client(mock_resp)

        with patch(
            "ai_engine.tools.business.create_ticket.httpx.AsyncClient", return_value=mock_client
        ):
            result = await CreateTicketTool().execute(
                {
                    "summary": "Printer broken",
                    "description": "Printer on 3rd floor not working",
                    "priority": "high",
                },
                ctx,
            )

        assert result["success"] is True
        assert result["ticket_id"] == "T-12345"
        call_json = mock_client.post.call_args[1]["json"]
        assert call_json["summary"] == "Printer broken"
        assert call_json["priority"] == "high"
        assert call_json["source"] == "ai_agent"
        assert "Bob" in call_json["description"]

    @pytest.mark.asyncio
    async def test_execute_no_summary(self, make_tool_context):
        ctx = make_tool_context()
        result = await CreateTicketTool().execute({"description": "detail"}, ctx)
        assert result["success"] is False
        assert "No summary" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_http_error(self, make_tool_context):
        ctx = make_tool_context()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "ai_engine.tools.business.create_ticket.httpx.AsyncClient", return_value=mock_client
        ):
            result = await CreateTicketTool().execute(
                {"summary": "Test", "description": "Test desc"},
                ctx,
            )

        assert result["success"] is False
        assert "Failed to create ticket" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_unknown_caller(self, make_tool_context, make_session):
        """When caller_name and caller_number are None, should use 'Unknown'."""
        session = make_session()
        ctx = make_tool_context(session=session, caller_name=None, caller_number=None)

        mock_resp = _mock_response(json_data={"ticket_id": "T-99"})
        mock_client = _mock_httpx_client(mock_resp)

        with patch(
            "ai_engine.tools.business.create_ticket.httpx.AsyncClient", return_value=mock_client
        ):
            result = await CreateTicketTool().execute(
                {"summary": "Issue", "description": "Some issue"},
                ctx,
            )

        assert result["success"] is True
