"""Zendesk Support REST API client."""

import base64

import httpx
import structlog

logger = structlog.get_logger()


class ZendeskClient:
    """HTTP client wrapping Zendesk Support REST API v2."""

    def __init__(
        self,
        subdomain: str,
        agent_email: str,
        api_token: str,
    ):
        self.base_url = f"https://{subdomain}.zendesk.com/api/v2"

        # Auth: Basic {email}/token:{api_token} base64
        credentials = f"{agent_email}/token:{api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict | list:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method, url, headers=self._headers, params=params, json=json_body
            )
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return resp.json()

    # -- Tickets ----------------------------------------------------------------

    async def search_tickets(self, query: str) -> list[dict]:
        """Search tickets using Zendesk search API.

        Args:
            query: Zendesk search query string (e.g. 'status:open requester:user@example.com').
        """
        result = await self._request("GET", "/search.json", params={"query": query})
        if isinstance(result, dict):
            return result.get("results", [])
        return []

    async def create_ticket(self, data: dict) -> dict:
        """Create a new Zendesk ticket.

        Args:
            data: Ticket payload, e.g. {"subject": "...", "comment": {"body": "..."}, "priority": "normal"}.
        """
        result = await self._request("POST", "/tickets.json", json_body={"ticket": data})
        if isinstance(result, dict):
            return result.get("ticket", {})
        return {}

    async def add_ticket_comment(self, ticket_id: int, comment: str, public: bool = True) -> dict:
        """Add a comment to an existing ticket.

        Args:
            ticket_id: Zendesk ticket ID.
            comment: Comment body text.
            public: Whether the comment is public (True) or internal note (False).
        """
        payload = {
            "ticket": {
                "comment": {
                    "body": comment,
                    "public": public,
                },
            },
        }
        result = await self._request("PUT", f"/tickets/{ticket_id}.json", json_body=payload)
        if isinstance(result, dict):
            return result.get("ticket", {})
        return {}

    async def get_user_by_phone(self, phone: str) -> dict | None:
        """Look up a Zendesk user by phone number.

        Args:
            phone: Phone number to search for.
        """
        result = await self._request(
            "GET", "/search.json", params={"query": f"type:user phone:{phone}"}
        )
        if isinstance(result, dict):
            results = result.get("results", [])
            if results:
                return results[0]
        return None

    # -- Connection test --------------------------------------------------------

    async def test_connection(self) -> dict:
        """Test connectivity by fetching current user info."""
        try:
            result = await self._request("GET", "/users/me.json")
            if isinstance(result, dict):
                user = result.get("user", {})
                return {
                    "success": True,
                    "message": f"Connected as {user.get('name', 'unknown')}",
                }
            return {"success": True, "message": "Connected to Zendesk"}
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {e!s}"}
