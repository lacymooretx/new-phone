"""ConnectWise Manage REST API client."""

import base64
import json

import httpx
import structlog
from redis.asyncio import Redis

logger = structlog.get_logger()

# Cache TTL: 1 hour for boards/statuses/types
CACHE_TTL = 3600


class ConnectWiseClient:
    """HTTP client wrapping ConnectWise Manage REST API v3.0."""

    def __init__(
        self,
        company_id: str,
        public_key: str,
        private_key: str,
        client_id: str,
        base_url: str = "https://na.myconnectwise.net",
        redis: Redis | None = None,
        tenant_id: str = "",
    ):
        self.company_id = company_id
        self.client_id = client_id
        self.base_url = f"{base_url.rstrip('/')}/v4_6_release/apis/3.0"
        self.redis = redis
        self.tenant_id = tenant_id

        # Auth: Basic {companyId}+{publicKey}:{privateKey} base64
        credentials = f"{company_id}+{public_key}:{private_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._headers = {
            "Authorization": f"Basic {encoded}",
            "clientId": client_id,
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

    async def _cached_get(self, cache_key: str, path: str, params: dict | None = None) -> list:
        """GET with Redis caching."""
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        result = await self._request("GET", path, params=params)
        if not isinstance(result, list):
            result = [result]

        if self.redis:
            await self.redis.setex(cache_key, CACHE_TTL, json.dumps(result))

        return result

    # ── Company endpoints ──────────────────────────────────────

    async def get_companies(self, query: str, page_size: int = 25) -> list[dict]:
        """Search companies by name."""
        params = {
            "conditions": f"name like '%{query}%'",
            "pageSize": str(page_size),
            "fields": "id,name,identifier",
        }
        result = await self._request("GET", "/company/companies", params=params)
        return result if isinstance(result, list) else []

    async def get_company(self, company_id: int) -> dict:
        """Get a single company by ID."""
        result = await self._request("GET", f"/company/companies/{company_id}")
        return result if isinstance(result, dict) else {}

    # ── Service ticket endpoints ──────────────────────────────

    async def create_ticket(
        self,
        summary: str,
        board_id: int | None = None,
        company_id: int | None = None,
        status_id: int | None = None,
        type_id: int | None = None,
        initial_description: str | None = None,
    ) -> dict:
        """Create a new service ticket."""
        body: dict = {"summary": summary}

        if board_id:
            body["board"] = {"id": board_id}
        if company_id:
            body["company"] = {"id": company_id}
        if status_id:
            body["status"] = {"id": status_id}
        if type_id:
            body["type"] = {"id": type_id}
        if initial_description:
            body["initialDescription"] = initial_description

        result = await self._request("POST", "/service/tickets", json_body=body)
        return result if isinstance(result, dict) else {}

    # ── Board / status / type endpoints ────────────────────────

    async def get_boards(self) -> list[dict]:
        """List service boards."""
        cache_key = f"cw:{self.tenant_id}:boards"
        return await self._cached_get(cache_key, "/service/boards", params={"pageSize": "100"})

    async def get_ticket_statuses(self, board_id: int) -> list[dict]:
        """List statuses for a service board."""
        cache_key = f"cw:{self.tenant_id}:board:{board_id}:statuses"
        return await self._cached_get(cache_key, f"/service/boards/{board_id}/statuses")

    async def get_ticket_types(self, board_id: int) -> list[dict]:
        """List types for a service board."""
        cache_key = f"cw:{self.tenant_id}:board:{board_id}:types"
        return await self._cached_get(cache_key, f"/service/boards/{board_id}/types")

    # ── System ─────────────────────────────────────────────────

    async def test_connection(self) -> dict:
        """Test connectivity by hitting /system/info."""
        try:
            result = await self._request("GET", "/system/info")
            return {
                "success": True,
                "message": f"Connected to ConnectWise Manage v{result.get('version', 'unknown')}",
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {e!s}"}
