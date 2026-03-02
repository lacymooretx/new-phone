"""Auth load test scenario.

Tests login, token refresh, and token validation under load.
Simulates the auth lifecycle: login -> use token on protected endpoint -> refresh.
"""

from __future__ import annotations

import logging

from locust import TaskSet, task

from conftest import API_PREFIX, pick_random_user

logger = logging.getLogger(__name__)


class AuthBehavior(TaskSet):
    """Auth-related load patterns.

    Weighted tasks:
      - login              (weight=1)  — full login flow
      - refresh_token      (weight=3)  — token refresh cycle
      - validate_token     (weight=5)  — hit a protected endpoint to validate token
    """

    def on_start(self) -> None:
        """Authenticate at the start of this task set."""
        self._do_login()

    def _do_login(self) -> None:
        """Perform a login and store tokens on the parent user."""
        creds = pick_random_user()
        with self.client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": creds["email"], "password": creds["password"]},
            name="POST /auth/login",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Handle MFA challenge — for load tests we treat it as success
                # (real MFA bypass not possible without TOTP secret).
                if data.get("mfa_required"):
                    response.success()
                    logger.debug("MFA required — login counted as success for load test")
                    return
                self.user.token_mgr.store_tokens(data)
                response.success()
            elif response.status_code == 401:
                # Expected when test credentials are wrong — mark as failure
                response.failure(f"Login failed: {response.text}")
            else:
                response.failure(f"Unexpected status {response.status_code}: {response.text}")

    @task(1)
    def login(self) -> None:
        """Full login flow — simulates a user signing in."""
        self._do_login()

    @task(3)
    def refresh_token(self) -> None:
        """Exchange refresh token for a new token pair."""
        rt = self.user.token_mgr.refresh_token
        if not rt:
            # No refresh token available — fall back to login
            self._do_login()
            return

        with self.client.post(
            f"{API_PREFIX}/auth/refresh",
            json={"refresh_token": rt},
            name="POST /auth/refresh",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.user.token_mgr.store_tokens(data)
                response.success()
            elif response.status_code == 401:
                # Token expired — re-login
                response.success()  # expected behavior, not an error
                self._do_login()
            else:
                response.failure(f"Unexpected status {response.status_code}: {response.text}")

    @task(5)
    def validate_token_on_protected_endpoint(self) -> None:
        """Hit the health endpoint (authenticated) to validate token."""
        headers = self.user.token_mgr.auth_header
        if not headers:
            self._do_login()
            headers = self.user.token_mgr.auth_header

        with self.client.get(
            f"{API_PREFIX}/health",
            headers=headers,
            name="GET /health (auth validation)",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                # Token expired — refresh
                response.success()
                self.refresh_token()
            else:
                response.failure(f"Unexpected status {response.status_code}")
