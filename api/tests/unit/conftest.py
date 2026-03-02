"""Shared fixtures for API unit tests — no external services required."""

import os
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Environment variables — MUST be set BEFORE any new_phone imports ────────
os.environ.setdefault("NP_JWT_SECRET_KEY", "test-jwt-secret-key-for-unit-tests-only-1234567890")
os.environ.setdefault("NP_TRUNK_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("NP_DB_HOST", "localhost")
os.environ.setdefault("NP_DB_NAME", "test_db")
os.environ.setdefault("NP_DB_ADMIN_USER", "test_admin")
os.environ.setdefault("NP_DB_ADMIN_PASSWORD", "test_pass")
os.environ.setdefault("NP_DB_APP_USER", "test_app")
os.environ.setdefault("NP_DB_APP_PASSWORD", "test_pass")
os.environ.setdefault("NP_REDIS_URL", "redis://localhost:6379/15")

# Import ALL models so SQLAlchemy mappers can resolve string-based relationships
# (e.g. Tenant → "AudioPrompt", User → "UserSSOLink") when any ORM constructor is used.
import new_phone.models.ai_agent_context
import new_phone.models.ai_agent_conversation
import new_phone.models.ai_agent_provider_config
import new_phone.models.ai_agent_tool_definition
import new_phone.models.audio_prompt
import new_phone.models.audit_log
import new_phone.models.boss_admin
import new_phone.models.building_webhook
import new_phone.models.caller_id_rule
import new_phone.models.camp_on
import new_phone.models.cdr
import new_phone.models.compliance_monitoring
import new_phone.models.conference_bridge
import new_phone.models.crm_config
import new_phone.models.cw_company_mapping
import new_phone.models.cw_config
import new_phone.models.cw_ticket_log
import new_phone.models.device
import new_phone.models.did
import new_phone.models.disposition
import new_phone.models.dnc
import new_phone.models.door_station
import new_phone.models.extension
import new_phone.models.follow_me
import new_phone.models.holiday_calendar
import new_phone.models.inbound_route
import new_phone.models.ivr_menu
import new_phone.models.outbound_route
import new_phone.models.page_group
import new_phone.models.paging_zone
import new_phone.models.panic_alert
import new_phone.models.parking_lot
import new_phone.models.phone_app_config
import new_phone.models.phone_model
import new_phone.models.queue
import new_phone.models.recording
import new_phone.models.recording_tier_config
import new_phone.models.ring_group
import new_phone.models.security_config
import new_phone.models.silent_intercom
import new_phone.models.sip_trunk
import new_phone.models.site
import new_phone.models.sms
import new_phone.models.sso_provider
import new_phone.models.sso_role_mapping
import new_phone.models.tenant
import new_phone.models.time_condition
import new_phone.models.user
import new_phone.models.user_sso_link
import new_phone.models.voicemail_box
import new_phone.models.voicemail_message
import new_phone.models.workforce_management  # noqa: F401
from new_phone.models.user import UserRole

# ── Deterministic UUIDs ─────────────────────────────────────────────────────
TENANT_ACME_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TENANT_GLOBEX_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
USER_MSP_ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
USER_MSP_TECH_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")
USER_ACME_ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000020")
USER_ACME_MANAGER_ID = uuid.UUID("00000000-0000-0000-0000-000000000021")
USER_ACME_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000022")

NOW = datetime(2024, 1, 1, tzinfo=UTC)


# ── Mock DB helpers ─────────────────────────────────────────────────────────


def make_scalar_result(value):
    """Mock Result whose scalar_one_or_none() returns *value*."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def make_scalars_result(values):
    """Mock Result whose scalars().all() returns *values* list."""
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = values
    scalars_mock.unique.return_value = scalars_mock
    result.scalars.return_value = scalars_mock
    return result


def make_rowcount_result(count):
    """Mock Result with a .rowcount attribute (for DELETE/UPDATE)."""
    result = MagicMock()
    result.rowcount = count
    return result


# ── ORM factories (MagicMock-based to avoid SQLAlchemy mapper issues) ──────


def make_user(**overrides):
    """Create a mock User object without triggering SQLAlchemy mapper config."""
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        email="test@example.com",
        password_hash="$2b$12$dummyhashfortestsonly00000000000000000000000000000000",
        first_name="Test",
        last_name="User",
        role=UserRole.TENANT_USER,
        is_active=True,
        mfa_enabled=False,
        mfa_secret=None,
        failed_login_attempts=0,
        locked_until=None,
        last_login_at=None,
        refresh_token_hash=None,
        refresh_token_expires_at=None,
        language="en",
        auth_method="local",
        deactivated_at=None,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    user = MagicMock()
    for key, value in defaults.items():
        setattr(user, key, value)
    return user


def make_tenant(**overrides):
    """Create a mock Tenant object without triggering SQLAlchemy mapper config."""
    defaults = dict(
        id=uuid.uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        domain=None,
        sip_domain="test-tenant.sip.local",
        is_active=True,
        notes=None,
        default_moh_prompt_id=None,
        default_language="en",
        deactivated_at=None,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    tenant = MagicMock()
    for key, value in defaults.items():
        setattr(tenant, key, value)
    return tenant


# ── Role-specific user fixtures ─────────────────────────────────────────────


@pytest.fixture
def msp_admin_user():
    return make_user(
        id=USER_MSP_ADMIN_ID,
        tenant_id=TENANT_ACME_ID,
        email="admin@msp.com",
        first_name="MSP",
        last_name="Admin",
        role=UserRole.MSP_SUPER_ADMIN,
    )


@pytest.fixture
def msp_tech_user():
    return make_user(
        id=USER_MSP_TECH_ID,
        tenant_id=TENANT_ACME_ID,
        email="tech@msp.com",
        first_name="MSP",
        last_name="Tech",
        role=UserRole.MSP_TECH,
    )


@pytest.fixture
def acme_admin_user():
    return make_user(
        id=USER_ACME_ADMIN_ID,
        tenant_id=TENANT_ACME_ID,
        email="admin@acme.com",
        first_name="Acme",
        last_name="Admin",
        role=UserRole.TENANT_ADMIN,
    )


@pytest.fixture
def acme_manager_user():
    return make_user(
        id=USER_ACME_MANAGER_ID,
        tenant_id=TENANT_ACME_ID,
        email="manager@acme.com",
        first_name="Acme",
        last_name="Manager",
        role=UserRole.TENANT_MANAGER,
    )


@pytest.fixture
def acme_user_user():
    return make_user(
        id=USER_ACME_USER_ID,
        tenant_id=TENANT_ACME_ID,
        email="user@acme.com",
        first_name="Acme",
        last_name="User",
        role=UserRole.TENANT_USER,
    )


# ── Mock DB session ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """AsyncMock of AsyncSession — reset between tests."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


# ── Patch set_tenant_context everywhere it's imported ───────────────────────

_RLS_MODULES = [
    "new_phone.services.user_service",
    "new_phone.services.extension_service",
    "new_phone.services.voicemail_service",
    "new_phone.services.queue_service",
    "new_phone.services.cdr_service",
    "new_phone.services.recording_service",
    "new_phone.services.ring_group_service",
    "new_phone.services.did_service",
    "new_phone.services.sip_trunk_service",
    "new_phone.services.inbound_route_service",
    "new_phone.services.outbound_route_service",
    "new_phone.deps.auth",
]


@pytest.fixture(autouse=True)
def mock_rls():
    """Patch set_tenant_context to a no-op in all service modules."""
    noop = AsyncMock()
    patches = []
    for mod in _RLS_MODULES:
        try:
            p = patch(f"{mod}.set_tenant_context", noop)
            p.start()
            patches.append(p)
        except (AttributeError, ModuleNotFoundError):
            pass
    yield
    for p in patches:
        p.stop()


# ── Async HTTP client for router tests ─────────────────────────────────────
# The `app` fixture is defined in each router test file (per-router approach)
# to avoid loading all 50+ routers via create_app().


@pytest.fixture
async def client(app):
    """Async HTTP client wired to the test app."""
    import httpx

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c
