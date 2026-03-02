"""Shared test utilities for load tests.

Provides token management, random data generation, and configurable
test credentials.  All settings come from environment variables so the
same test suite works against local dev and staging environments.
"""

from __future__ import annotations

import logging
import os
import random
import string
import uuid

from faker import Faker

logger = logging.getLogger(__name__)
fake = Faker()

# ---------------------------------------------------------------------------
# Environment-driven configuration
# ---------------------------------------------------------------------------

API_HOST = os.getenv("NP_LOAD_HOST", "http://localhost:8000")
API_PREFIX = os.getenv("NP_LOAD_API_PREFIX", "/api/v1")

# Default test user credentials (override via env for CI/staging)
TEST_USER_EMAIL = os.getenv("NP_LOAD_USER_EMAIL", "admin@test.local")
TEST_USER_PASSWORD = os.getenv("NP_LOAD_USER_PASSWORD", "TestPassword123!")

# If multiple test accounts exist, provide a comma-separated list.
# Format: email:password,email:password,...
TEST_USERS_CSV = os.getenv("NP_LOAD_USERS", "")

# Default tenant ID to operate against (UUID). If empty, we discover it
# after login from /tenants.
DEFAULT_TENANT_ID = os.getenv("NP_LOAD_TENANT_ID", "")


def get_test_users() -> list[dict[str, str]]:
    """Return a list of {email, password} dicts for all test accounts."""
    users: list[dict[str, str]] = []
    if TEST_USERS_CSV:
        for pair in TEST_USERS_CSV.split(","):
            pair = pair.strip()
            if ":" in pair:
                email, password = pair.split(":", 1)
                users.append({"email": email.strip(), "password": password.strip()})
    if not users:
        users.append({"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD})
    return users


def pick_random_user() -> dict[str, str]:
    """Choose a random test account for a simulated user session."""
    users = get_test_users()
    return random.choice(users)


# ---------------------------------------------------------------------------
# Token management helper
# ---------------------------------------------------------------------------


class TokenManager:
    """Stores and refreshes JWT tokens for a single Locust user."""

    def __init__(self) -> None:
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.tenant_id: str | None = DEFAULT_TENANT_ID or None

    @property
    def auth_header(self) -> dict[str, str]:
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    def store_tokens(self, data: dict) -> None:
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")

    def clear(self) -> None:
        self.access_token = None
        self.refresh_token = None


# ---------------------------------------------------------------------------
# Random data generators
# ---------------------------------------------------------------------------


def random_extension_number() -> str:
    """Generate a random 3-4 digit extension number."""
    return str(random.randint(1000, 9999))


def random_mailbox_number() -> str:
    """Generate a random voicemail box number."""
    return str(random.randint(8000, 8999))


def random_pin() -> str:
    """Generate a random 4-6 digit PIN."""
    length = random.randint(4, 6)
    return "".join(random.choices(string.digits, k=length))


def random_queue_number() -> str:
    """Generate a random queue number."""
    return str(random.randint(5000, 5999))


def random_phone_number() -> str:
    """Generate a random E.164 phone number."""
    return f"+1{random.randint(2000000000, 9999999999)}"


def random_uuid() -> str:
    """Generate a random UUID string."""
    return str(uuid.uuid4())


def random_extension_create_payload() -> dict:
    """Return a valid payload for POST /tenants/{id}/extensions."""
    ext_num = random_extension_number()
    return {
        "extension_number": ext_num,
        "internal_cid_name": fake.name(),
        "internal_cid_number": ext_num,
        "external_cid_name": fake.company(),
        "external_cid_number": random_phone_number(),
        "dnd_enabled": False,
        "call_waiting": True,
        "max_registrations": 3,
        "outbound_cid_mode": "internal",
        "class_of_service": "domestic",
        "recording_policy": "never",
    }


def random_voicemail_box_create_payload() -> dict:
    """Return a valid payload for POST /tenants/{id}/voicemail-boxes."""
    return {
        "mailbox_number": random_mailbox_number(),
        "pin": random_pin(),
        "greeting_type": "default",
        "email_notification": True,
        "notification_email": fake.email(),
        "max_messages": 100,
    }


def random_queue_create_payload() -> dict:
    """Return a valid payload for POST /tenants/{id}/queues."""
    return {
        "name": f"Queue {fake.word().capitalize()}",
        "queue_number": random_queue_number(),
        "description": fake.sentence(),
        "strategy": "longest-idle-agent",
        "max_wait_time": 300,
        "ring_timeout": 30,
        "wrapup_time": 10,
        "enabled": True,
    }
