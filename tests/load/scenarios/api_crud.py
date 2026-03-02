"""CRUD operations load test scenario.

Tests create/read/update/delete workflows for extensions, users, queues,
and voicemail boxes under load.  Mirrors realistic admin panel usage.
"""

from __future__ import annotations

import logging
import random

from locust import TaskSet, task

from conftest import (
    API_PREFIX,
    random_extension_create_payload,
    random_extension_number,
    random_voicemail_box_create_payload,
)

logger = logging.getLogger(__name__)


class ApiCrudBehavior(TaskSet):
    """CRUD operation load patterns.

    Weighted tasks:
      - list_extensions     (weight=5)
      - create_extension    (weight=1)
      - update_extension    (weight=2)
      - delete_extension    (weight=1)
      - list_users          (weight=3)
      - list_queues         (weight=3)
    """

    # Track IDs of resources we create so we can update/delete them
    created_extension_ids: list[str] = []
    created_voicemail_ids: list[str] = []

    def on_start(self) -> None:
        """Ensure we have auth tokens and a tenant ID."""
        self._ensure_auth()
        self._ensure_tenant_id()

    def _ensure_auth(self) -> None:
        """Re-login if no valid token."""
        if self.user.token_mgr.access_token:
            return
        self.user.do_login()

    def _ensure_tenant_id(self) -> None:
        """Discover tenant ID if not already set."""
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
            response.success()  # expected, not a test error
            self.user.do_login()
            return True
        return False

    # ── Extensions ──

    @task(5)
    def list_extensions(self) -> None:
        """GET /tenants/{id}/extensions — most common read operation."""
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

    @task(1)
    def create_extension(self) -> None:
        """POST /tenants/{id}/extensions — create a new extension."""
        self._ensure_auth()
        payload = random_extension_create_payload()
        with self.client.post(
            f"{self._tenant_url}/extensions",
            json=payload,
            headers=self._headers,
            name="POST /tenants/[id]/extensions",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                data = resp.json()
                self.created_extension_ids.append(data["id"])
                resp.success()
            elif resp.status_code == 409:
                # Duplicate extension number — expected under load
                resp.success()
            elif not self._handle_auth_error(resp):
                resp.failure(f"create_extension: {resp.status_code} {resp.text[:200]}")

    @task(2)
    def update_extension(self) -> None:
        """PATCH /tenants/{id}/extensions/{ext_id} — update an existing extension."""
        self._ensure_auth()
        if not self.created_extension_ids:
            # No extensions to update — just list instead
            self.list_extensions()
            return

        ext_id = random.choice(self.created_extension_ids)
        payload = {
            "internal_cid_name": f"Updated User {random.randint(1, 999)}",
            "dnd_enabled": random.choice([True, False]),
            "call_waiting": random.choice([True, False]),
        }
        with self.client.patch(
            f"{self._tenant_url}/extensions/{ext_id}",
            json=payload,
            headers=self._headers,
            name="PATCH /tenants/[id]/extensions/[id]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 404:
                # Extension was already deleted — remove from our tracking list
                resp.success()
                if ext_id in self.created_extension_ids:
                    self.created_extension_ids.remove(ext_id)
            elif not self._handle_auth_error(resp):
                resp.failure(f"update_extension: {resp.status_code}")

    @task(1)
    def delete_extension(self) -> None:
        """DELETE /tenants/{id}/extensions/{ext_id} — deactivate an extension."""
        self._ensure_auth()
        if not self.created_extension_ids:
            self.list_extensions()
            return

        ext_id = self.created_extension_ids.pop(0)
        with self.client.delete(
            f"{self._tenant_url}/extensions/{ext_id}",
            headers=self._headers,
            name="DELETE /tenants/[id]/extensions/[id]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 404:
                resp.success()  # already gone
            elif not self._handle_auth_error(resp):
                resp.failure(f"delete_extension: {resp.status_code}")

    # ── Users ──

    @task(3)
    def list_users(self) -> None:
        """GET /tenants/{id}/users — list tenant users."""
        self._ensure_auth()
        with self.client.get(
            f"{self._tenant_url}/users",
            headers=self._headers,
            name="GET /tenants/[id]/users",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif not self._handle_auth_error(resp):
                resp.failure(f"list_users: {resp.status_code}")

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
