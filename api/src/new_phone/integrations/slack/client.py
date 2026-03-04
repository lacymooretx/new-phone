"""Slack Web API client."""

import httpx
import structlog

logger = structlog.get_logger()


class SlackClient:
    """HTTP client wrapping Slack Web API."""

    def __init__(self, bot_token: str):
        self.base_url = "https://slack.com/api"
        self._headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json_body: dict | None = None,
    ) -> dict:
        url = f"{self.base_url}/{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method, url, headers=self._headers, json=json_body
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                error = data.get("error", "unknown_error")
                raise httpx.HTTPStatusError(
                    f"Slack API error: {error}",
                    request=resp.request,
                    response=resp,
                )
            return data

    # -- Messaging --------------------------------------------------------------

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict] | None = None,
    ) -> dict:
        """Send a message to a channel or conversation.

        Args:
            channel: Channel ID or name.
            text: Fallback text (also used for notifications).
            blocks: Optional Block Kit blocks for rich formatting.
        """
        payload: dict = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        return await self._request("POST", "chat.postMessage", json_body=payload)

    async def send_dm(self, user_id: str, text: str) -> dict:
        """Open a DM conversation and send a message.

        Args:
            user_id: Slack user ID.
            text: Message text.
        """
        # Open or retrieve existing DM conversation
        conv = await self._request(
            "POST", "conversations.open", json_body={"users": user_id}
        )
        channel_id = conv.get("channel", {}).get("id")
        if not channel_id:
            raise ValueError(f"Could not open DM with user {user_id}")
        return await self.send_message(channel=channel_id, text=text)

    async def post_to_channel(self, channel_id: str, text: str) -> dict:
        """Post a plain text message to a specific channel by ID.

        Args:
            channel_id: Slack channel ID.
            text: Message text.
        """
        return await self.send_message(channel=channel_id, text=text)

    # -- Connection test --------------------------------------------------------

    async def test_connection(self) -> dict:
        """Test connectivity by calling auth.test."""
        try:
            result = await self._request("POST", "auth.test")
            return {
                "success": True,
                "message": f"Connected as {result.get('bot_id', 'unknown')} in team {result.get('team', 'unknown')}",
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"Slack API error: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {e!s}"}
