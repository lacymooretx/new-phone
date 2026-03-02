"""Main Locust configuration for New Phone API load tests.

Imports all scenario modules and defines the composite user class.
Each simulated user authenticates on start and cycles through weighted
task sets that model real-world traffic patterns.

Usage:
    locust -f locustfile.py --headless -u 10 -r 2 -t 30s
    locust -f locustfile.py  # web UI at http://localhost:8089
"""

from __future__ import annotations

import logging
import sys
import time

from locust import HttpUser, between, events

from conftest import API_HOST, API_PREFIX, TokenManager, pick_random_user
from scenarios.api_crud import ApiCrudBehavior
from scenarios.auth import AuthBehavior
from scenarios.concurrent_calls import ConcurrentCallsBehavior
from scenarios.read_heavy import ReadHeavyBehavior

logger = logging.getLogger(__name__)


class NewPhoneUser(HttpUser):
    """Composite user simulating realistic PBX API traffic.

    Traffic distribution:
      - ReadHeavyBehavior        (weight=5)  — dashboard browsing, CDR views
      - ApiCrudBehavior          (weight=3)  — admin CRUD on extensions/users/queues
      - ConcurrentCallsBehavior  (weight=2)  — wallboard/call monitoring polling
      - AuthBehavior             (weight=1)  — login/refresh cycles
    """

    # Think time between requests: 1-3 seconds
    wait_time = between(1, 3)

    # Default host — overridden via CLI or environment
    host = API_HOST

    # Task set weights — read-heavy traffic dominates
    tasks = {
        ReadHeavyBehavior: 5,
        ApiCrudBehavior: 3,
        ConcurrentCallsBehavior: 2,
        AuthBehavior: 1,
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.token_mgr = TokenManager()

    def on_start(self) -> None:
        """Authenticate and discover tenant at the start of each user session."""
        self.do_login()
        self.discover_tenant_id()

    def do_login(self) -> None:
        """Perform login and store JWT tokens."""
        creds = pick_random_user()
        try:
            response = self.client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": creds["email"], "password": creds["password"]},
                name="POST /auth/login (session init)",
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if not data.get("mfa_required"):
                    self.token_mgr.store_tokens(data)
                    logger.debug("User authenticated: %s", creds["email"])
                else:
                    logger.warning(
                        "MFA required for %s — load test needs non-MFA account",
                        creds["email"],
                    )
            else:
                logger.error(
                    "Login failed for %s: %s %s",
                    creds["email"],
                    response.status_code,
                    response.text[:200],
                )
        except Exception:
            logger.exception("Login request failed for %s", creds["email"])

    def discover_tenant_id(self) -> None:
        """Discover the first available tenant ID after login.

        Uses GET /tenants to find a tenant this user can access.
        If a tenant ID was pre-configured via env var, skip discovery.
        """
        if self.token_mgr.tenant_id:
            return

        headers = self.token_mgr.auth_header
        if not headers:
            return

        try:
            response = self.client.get(
                f"{API_PREFIX}/tenants",
                headers=headers,
                name="GET /tenants (discovery)",
                timeout=10,
            )
            if response.status_code == 200:
                tenants = response.json()
                if tenants:
                    self.token_mgr.tenant_id = tenants[0]["id"]
                    logger.debug("Discovered tenant: %s", self.token_mgr.tenant_id)
                else:
                    logger.warning("No tenants found for this user")
            else:
                logger.warning(
                    "Tenant discovery failed: %s %s",
                    response.status_code,
                    response.text[:200],
                )
        except Exception:
            logger.exception("Tenant discovery request failed")


# ---------------------------------------------------------------------------
# Event hooks for test lifecycle reporting
# ---------------------------------------------------------------------------


@events.test_start.add_listener
def on_test_start(environment, **kwargs) -> None:
    """Log test configuration at startup."""
    logger.info("=" * 60)
    logger.info("New Phone API Load Test Starting")
    logger.info("  Target host: %s", environment.host)
    logger.info("  API prefix:  %s", API_PREFIX)
    if environment.parsed_options:
        logger.info("  Users:       %s", getattr(environment.parsed_options, "num_users", "?"))
        logger.info("  Spawn rate:  %s", getattr(environment.parsed_options, "spawn_rate", "?"))
        logger.info("  Run time:    %s", getattr(environment.parsed_options, "run_time", "?"))
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs) -> None:
    """Log summary and check against performance targets."""
    logger.info("=" * 60)
    logger.info("New Phone API Load Test Complete")

    stats = environment.runner.stats
    total = stats.total

    logger.info("  Total requests:  %d", total.num_requests)
    logger.info("  Total failures:  %d", total.num_failures)
    if total.num_requests > 0:
        error_rate = (total.num_failures / total.num_requests) * 100
        logger.info("  Error rate:      %.2f%%", error_rate)
        logger.info("  Avg response:    %d ms", total.avg_response_time)
        logger.info("  p95 response:    %d ms", total.get_response_time_percentile(0.95) or 0)
        logger.info("  p99 response:    %d ms", total.get_response_time_percentile(0.99) or 0)
        logger.info("  Requests/sec:    %.2f", total.total_rps)

        # Performance gate — non-zero exit for CI pipelines
        p95 = total.get_response_time_percentile(0.95) or 0
        failed = False

        if error_rate > 1.0:
            logger.error("FAIL: Error rate %.2f%% exceeds 1%% threshold", error_rate)
            failed = True
        if p95 > 500:
            logger.warning("WARN: p95 response time %d ms exceeds 500ms target", p95)

        # Check auth-specific latency
        for entry in stats.entries.values():
            if "login" in entry.name.lower():
                login_p95 = entry.get_response_time_percentile(0.95) or 0
                if login_p95 > 500:
                    logger.warning(
                        "WARN: Login p95 %d ms exceeds 500ms target", login_p95
                    )

        if failed and environment.parsed_options and getattr(
            environment.parsed_options, "headless", False
        ):
            logger.error("Load test FAILED performance gates")
            # Let the test complete but signal failure
            environment.process_exit_code = 1
    else:
        logger.warning("No requests were made during the test")

    logger.info("=" * 60)
