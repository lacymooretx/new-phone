"""Tests for new_phone.routers.ten_dlc — Brand and Campaign CRUD, registration, status."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.routers import ten_dlc
from tests.unit.conftest import TENANT_ACME_ID

TENANT_ID = TENANT_ACME_ID
BRAND_ID = uuid.UUID("00000000-0000-0000-0000-dddddddddddd")
CAMPAIGN_ID = uuid.UUID("00000000-0000-0000-0000-eeeeeeeeeeee")
NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _mock_brand(**overrides):
    defaults = dict(
        id=BRAND_ID,
        tenant_id=TENANT_ID,
        name="Acme Brand",
        ein="12-3456789",
        ein_issuing_country="US",
        brand_type="small_business",
        vertical="technology",
        website="https://acme.com",
        status="draft",
        provider_brand_id=None,
        rejection_reason=None,
        submitted_at=None,
        approved_at=None,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _mock_campaign(**overrides):
    defaults = dict(
        id=CAMPAIGN_ID,
        tenant_id=TENANT_ID,
        brand_id=BRAND_ID,
        name="Customer Care",
        use_case="customer_care",
        description="Customer support messaging",
        sample_messages=["Hi, how can we help?"],
        message_flow="Customer texts in, agent replies",
        help_message="Reply HELP for support",
        opt_out_message="Reply STOP to unsubscribe",
        opt_in_keywords="START",
        opt_out_keywords="STOP",
        help_keywords="HELP",
        number_pool=None,
        status="draft",
        provider_campaign_id=None,
        rejection_reason=None,
        submitted_at=None,
        approved_at=None,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


@pytest.fixture
def app(mock_db, acme_admin_user):
    test_app = FastAPI()
    test_app.include_router(ten_dlc.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: acme_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


# ══════════════════════════════════════════════════════════════════════════
# Brands
# ══════════════════════════════════════════════════════════════════════════


class TestCreateBrand:
    async def test_success_returns_201(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.create_brand = AsyncMock(return_value=_mock_brand())
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/brands",
                json={
                    "name": "Acme Brand",
                    "ein": "12-3456789",
                    "brand_type": "small_business",
                    "vertical": "technology",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Acme Brand"


class TestListBrands:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.list_brands = AsyncMock(return_value=[_mock_brand()])
            resp = await client.get(f"/api/v1/tenants/{TENANT_ID}/10dlc/brands")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1


class TestGetBrand:
    async def test_found_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.get_brand = AsyncMock(return_value=_mock_brand())
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/brands/{BRAND_ID}"
            )
        assert resp.status_code == 200

    async def test_not_found_returns_404(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.get_brand = AsyncMock(return_value=None)
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/brands/{BRAND_ID}"
            )
        assert resp.status_code == 404


class TestUpdateBrand:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.update_brand = AsyncMock(
                return_value=_mock_brand(name="Updated Brand")
            )
            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/brands/{BRAND_ID}",
                json={"name": "Updated Brand"},
            )
        assert resp.status_code == 200

    async def test_bad_request_returns_400(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.update_brand = AsyncMock(
                side_effect=ValueError("Cannot update approved brand")
            )
            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/brands/{BRAND_ID}",
                json={"name": "Updated Brand"},
            )
        assert resp.status_code == 400


class TestRegisterBrand:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.register_brand = AsyncMock(
                return_value=_mock_brand(status="pending")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/brands/{BRAND_ID}/register"
            )
        assert resp.status_code == 200

    async def test_bad_request_returns_400(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.register_brand = AsyncMock(
                side_effect=ValueError("Brand must be in draft status")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/brands/{BRAND_ID}/register"
            )
        assert resp.status_code == 400


class TestCheckBrandStatus:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.check_brand_status = AsyncMock(
                return_value=_mock_brand(status="approved")
            )
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/brands/{BRAND_ID}/status"
            )
        assert resp.status_code == 200

    async def test_not_found_returns_404(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.check_brand_status = AsyncMock(
                side_effect=ValueError("Brand not found")
            )
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/brands/{BRAND_ID}/status"
            )
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════
# Campaigns
# ══════════════════════════════════════════════════════════════════════════


class TestCreateCampaign:
    async def test_success_returns_201(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.create_campaign = AsyncMock(return_value=_mock_campaign())
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns",
                json={
                    "brand_id": str(BRAND_ID),
                    "name": "Customer Care",
                    "use_case": "customer_care",
                    "description": "Customer support messaging",
                    "sample_messages": ["Hi, how can we help?"],
                    "message_flow": "Customer texts in, agent replies",
                    "help_message": "Reply HELP for support",
                    "opt_out_message": "Reply STOP to unsubscribe",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Customer Care"

    async def test_bad_request_returns_400(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.create_campaign = AsyncMock(
                side_effect=ValueError("Brand not approved")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns",
                json={
                    "brand_id": str(BRAND_ID),
                    "name": "Customer Care",
                    "use_case": "customer_care",
                    "description": "Customer support messaging",
                    "sample_messages": ["Hi, how can we help?"],
                    "message_flow": "Customer texts in, agent replies",
                    "help_message": "Reply HELP for support",
                    "opt_out_message": "Reply STOP to unsubscribe",
                },
            )
        assert resp.status_code == 400


class TestListCampaigns:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.list_campaigns = AsyncMock(return_value=[_mock_campaign()])
            resp = await client.get(f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestGetCampaign:
    async def test_found_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.get_campaign = AsyncMock(return_value=_mock_campaign())
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns/{CAMPAIGN_ID}"
            )
        assert resp.status_code == 200

    async def test_not_found_returns_404(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.get_campaign = AsyncMock(return_value=None)
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns/{CAMPAIGN_ID}"
            )
        assert resp.status_code == 404


class TestUpdateCampaign:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.update_campaign = AsyncMock(
                return_value=_mock_campaign(name="Updated Campaign")
            )
            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns/{CAMPAIGN_ID}",
                json={"name": "Updated Campaign"},
            )
        assert resp.status_code == 200

    async def test_bad_request_returns_400(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.update_campaign = AsyncMock(
                side_effect=ValueError("Cannot update approved campaign")
            )
            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns/{CAMPAIGN_ID}",
                json={"name": "Updated Campaign"},
            )
        assert resp.status_code == 400


class TestRegisterCampaign:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.register_campaign = AsyncMock(
                return_value=_mock_campaign(status="pending")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns/{CAMPAIGN_ID}/register"
            )
        assert resp.status_code == 200

    async def test_bad_request_returns_400(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.register_campaign = AsyncMock(
                side_effect=ValueError("Campaign must be in draft status")
            )
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns/{CAMPAIGN_ID}/register"
            )
        assert resp.status_code == 400


class TestCheckCampaignStatus:
    async def test_success_returns_200(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.check_campaign_status = AsyncMock(
                return_value=_mock_campaign(status="approved")
            )
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns/{CAMPAIGN_ID}/status"
            )
        assert resp.status_code == 200

    async def test_not_found_returns_404(self, app, client):
        with patch("new_phone.routers.ten_dlc.TenDLCService") as MockSvc:
            MockSvc.return_value.check_campaign_status = AsyncMock(
                side_effect=ValueError("Campaign not found")
            )
            resp = await client.get(
                f"/api/v1/tenants/{TENANT_ID}/10dlc/campaigns/{CAMPAIGN_ID}/status"
            )
        assert resp.status_code == 404
