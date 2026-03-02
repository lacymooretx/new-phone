"""Read-heavy load test scenario.

Simulates the most common traffic pattern: users browsing dashboards,
checking CDRs, viewing recordings, and monitoring queues.  This is the
dominant workload for a multi-tenant PBX UI.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from locust import TaskSet, task

from conftest import API_PREFIX, random_phone_number

logger = logging.getLogger(__name__)


class ReadHeavyBehavior(TaskSet):
    """Read-heavy load patterns (most common traffic).

    Weighted tasks:
      - get_health           (weight=1)
      - list_cdrs            (weight=5)
      - list_recordings      (weight=3)
      - list_extensions      (weight=5)
      - list_queues          (weight=3)
      - list_voicemail       (weight=2)
      - search_cdrs          (weight=2)
    """

    def on_start(self) -> None:
        """Ensure we have auth tokens and a tenant ID."""
        self._ensure_auth()
        self._ensure_tenant_id()

    def _ensure_auth(self) -> None:
        if self.user.token_mgr.access_token:
            return
        self.user.do_login()

    def _ensure_tenant_id(self) -> None:
        if self.user.token_mgr.tenant_id:
            return
        self.user.discover_tenant_id()

    @property
    def _headers(self) -> dict[str, str]:
        return self.user.token_mgr.auth_header

    @property
    def _tenant_url(self) -> str:
        tid = self.user.token_mgr.tenant_id
        return f"{API_PREFIX}/tenants/{tid}"

    def _handle_auth_error(self, response) -> bool:
        """Handle 401 by re-logging in.  Returns True if it was a 401."""
        if response.status_code == 401:
            response.success()
            self.user.do_login()
            return True
        return False

    # ── Health ──

    @task(1)
    def get_health(self) -> None:
        """GET /health — lightweight health check."""
        with self.client.get(
            f"{API_PREFIX}/health",
            headers=self._headers,
            name="GET /health",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"health: {resp.status_code}")

    # ── CDRs ──

    @task(5)
    def list_cdrs(self) -> None:
        """GET /tenants/{id}/cdrs — list recent call detail records."""
        self._ensure_auth()
        with self.client.get(
            f"{self._tenant_url}/cdrs",
            headers=self._headers,
            params={"limit": 50, "offset": 0},
            name="GET /tenants/[id]/cdrs",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif not self._handle_auth_error(resp):
                resp.failure(f"list_cdrs: {resp.status_code}")

    @task(2)
    def search_cdrs(self) -> None:
        """GET /tenants/{id}/cdrs with date range filters — filtered CDR search."""
        self._ensure_auth()
        now = datetime.now(timezone.utc)
        date_from = (now - timedelta(days=random.randint(1, 30))).isoformat()
        date_to = now.isoformat()
        direction = random.choice(["inbound", "outbound", None])

        params: dict = {
            "date_from": date_from,
            "date_to": date_to,
            "limit": random.choice([25, 50, 100]),
            "offset": 0,
        }
        if direction:
            params["direction"] = direction

        with self.client.get(
            f"{self._tenant_url}/cdrs",
            headers=self._headers,
            params=params,
            name="GET /tenants/[id]/cdrs (filtered)",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif not self._handle_auth_error(resp):
                resp.failure(f"search_cdrs: {resp.status_code}")

    # ── Recordings ──

    @task(3)
    def list_recordings(self) -> None:
        """GET /tenants/{id}/recordings — list call recordings."""
        self._ensure_auth()
        with self.client.get(
            f"{self._tenant_url}/recordings",
            headers=self._headers,
            params={"limit": 50, "offset": 0},
            name="GET /tenants/[id]/recordings",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif not self._handle_auth_error(resp):
                resp.failure(f"list_recordings: {resp.status_code}")

    # ── Extensions ──

    @task(5)
    def list_extensions(self) -> None:
        """GET /tenants/{id}/extensions — list all extensions."""
        self._ensure_auth()
        with self.client.get(
            f"{self._tenant_url}/extensions",
            headers=self._headers,
            name="GET /tenants/[id]/extensions",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif not self._handle_auth_error(resp):
                resp.failure(f"list_extensions: {resp.status_code}")

    # ── Queues ──

    @task(3)
    def list_queues(self) -> None:
        """GET /tenants/{id}/queues — list call queues."""
        self._ensure_auth()
        with self.client.get(
            f"{self._tenant_url}/queues",
            headers=self._headers,
            name="GET /tenants/[id]/queues",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif not self._handle_auth_error(resp):
                resp.failure(f"list_queues: {resp.status_code}")

    # ── Voicemail ──

    @task(2)
    def list_voicemail(self) -> None:
        """GET /tenants/{id}/voicemail-boxes — list voicemail boxes."""
        self._ensure_auth()
        with self.client.get(
            f"{self._tenant_url}/voicemail-boxes",
            headers=self._headers,
            name="GET /tenants/[id]/voicemail-boxes",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif not self._handle_auth_error(resp):
                resp.failure(f"list_voicemail: {resp.status_code}")
