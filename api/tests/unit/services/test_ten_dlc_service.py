"""Tests for new_phone.services.ten_dlc_service — 10DLC brand/campaign/compliance."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from new_phone.schemas.ten_dlc import BrandCreate, BrandUpdate, CampaignCreate, CampaignUpdate
from new_phone.services.ten_dlc_service import TenDLCService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_brand(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Acme Corp",
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
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_campaign(**overrides):
    brand_id = overrides.pop("brand_id", uuid.uuid4())
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        brand_id=brand_id,
        name="Customer Care",
        use_case="customer_care",
        description="Customer support messaging",
        sample_messages=["Hello!", "Your ticket is updated."],
        message_flow="Customer initiates contact",
        help_message="Reply HELP for help",
        opt_out_message="Reply STOP to opt out",
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
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ── Brand CRUD ───────────────────────────────────────────────────────────


class TestCreateBrand:
    async def test_success(self, mock_db):
        data = BrandCreate(
            name="New Brand",
            ein="99-9999999",
            brand_type="small_business",
            vertical="healthcare",
        )
        service = TenDLCService(mock_db)
        await service.create_brand(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()


class TestListBrands:
    async def test_returns_brands(self, mock_db):
        b1 = _make_brand()
        b2 = _make_brand()
        mock_db.execute.return_value = make_scalars_result([b1, b2])

        service = TenDLCService(mock_db)
        result = await service.list_brands(TENANT_ACME_ID)
        assert len(result) == 2


class TestGetBrand:
    async def test_found(self, mock_db):
        brand = _make_brand()
        mock_db.execute.return_value = make_scalar_result(brand)
        service = TenDLCService(mock_db)
        result = await service.get_brand(TENANT_ACME_ID, brand.id)
        assert result is brand

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenDLCService(mock_db)
        result = await service.get_brand(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestUpdateBrand:
    async def test_success_draft_status(self, mock_db):
        brand = _make_brand(status="draft")
        mock_db.execute.return_value = make_scalar_result(brand)
        data = BrandUpdate(name="Updated Brand")

        service = TenDLCService(mock_db)
        await service.update_brand(TENANT_ACME_ID, brand.id, data)
        assert brand.name == "Updated Brand"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenDLCService(mock_db)
        with pytest.raises(ValueError, match="Brand not found"):
            await service.update_brand(TENANT_ACME_ID, uuid.uuid4(), BrandUpdate(name="X"))

    async def test_cannot_update_pending_raises(self, mock_db):
        brand = _make_brand(status="pending")
        mock_db.execute.return_value = make_scalar_result(brand)
        service = TenDLCService(mock_db)
        with pytest.raises(ValueError, match="Cannot update brand"):
            await service.update_brand(TENANT_ACME_ID, brand.id, BrandUpdate(name="X"))

    async def test_can_update_rejected(self, mock_db):
        brand = _make_brand(status="rejected")
        mock_db.execute.return_value = make_scalar_result(brand)
        data = BrandUpdate(name="Fixed Brand")

        service = TenDLCService(mock_db)
        await service.update_brand(TENANT_ACME_ID, brand.id, data)
        assert brand.name == "Fixed Brand"


# ── Register Brand ───────────────────────────────────────────────────────


class TestRegisterBrand:
    @patch("new_phone.sms.factory.get_tenant_default_provider")
    async def test_success_with_provider(self, mock_get_provider, mock_db):
        brand = _make_brand(status="draft")
        mock_db.execute.return_value = make_scalar_result(brand)

        mock_config = MagicMock()
        mock_config.provider_type = "clearlyip"
        mock_provider = MagicMock()
        mock_provider.register_brand = AsyncMock(return_value={"brand_id": "BRAND_123"})
        mock_get_provider.return_value = (mock_config, mock_provider)

        service = TenDLCService(mock_db)
        await service.register_brand(TENANT_ACME_ID, brand.id)
        assert brand.status == "pending"
        assert brand.provider_brand_id == "BRAND_123"
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenDLCService(mock_db)
        with pytest.raises(ValueError, match="Brand not found"):
            await service.register_brand(TENANT_ACME_ID, uuid.uuid4())

    async def test_cannot_register_approved_raises(self, mock_db):
        brand = _make_brand(status="approved")
        mock_db.execute.return_value = make_scalar_result(brand)
        service = TenDLCService(mock_db)
        with pytest.raises(ValueError, match="Cannot register brand"):
            await service.register_brand(TENANT_ACME_ID, brand.id)


# ── Check Brand Status ───────────────────────────────────────────────────


class TestCheckBrandStatus:
    @patch("new_phone.sms.factory.get_tenant_default_provider")
    async def test_updates_to_approved(self, mock_get_provider, mock_db):
        brand = _make_brand(status="pending", provider_brand_id="BRAND_123")
        mock_db.execute.return_value = make_scalar_result(brand)

        mock_config = MagicMock()
        mock_provider = MagicMock()
        mock_provider.check_brand_status = AsyncMock(return_value={"status": "approved"})
        mock_get_provider.return_value = (mock_config, mock_provider)

        service = TenDLCService(mock_db)
        await service.check_brand_status(TENANT_ACME_ID, brand.id)
        assert brand.status == "approved"
        assert brand.approved_at is not None

    async def test_not_pending_returns_unchanged(self, mock_db):
        brand = _make_brand(status="approved")
        mock_db.execute.return_value = make_scalar_result(brand)

        service = TenDLCService(mock_db)
        result = await service.check_brand_status(TENANT_ACME_ID, brand.id)
        assert result.status == "approved"


# ── Campaign CRUD ────────────────────────────────────────────────────────


class TestCreateCampaign:
    async def test_success(self, mock_db):
        brand = _make_brand()
        mock_db.execute.return_value = make_scalar_result(brand)

        data = CampaignCreate(
            brand_id=brand.id,
            name="Support Campaign",
            use_case="customer_care",
            description="Customer support",
            sample_messages=["Hello!"],
            message_flow="Customer initiates",
            help_message="Reply HELP",
            opt_out_message="Reply STOP",
        )
        service = TenDLCService(mock_db)
        await service.create_campaign(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    async def test_brand_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        data = CampaignCreate(
            brand_id=uuid.uuid4(),
            name="X",
            use_case="customer_care",
            description="X",
            sample_messages=["X"],
            message_flow="X",
            help_message="X",
            opt_out_message="X",
        )
        service = TenDLCService(mock_db)
        with pytest.raises(ValueError, match="Brand not found"):
            await service.create_campaign(TENANT_ACME_ID, data)


class TestUpdateCampaign:
    async def test_success(self, mock_db):
        campaign = _make_campaign(status="draft")
        mock_db.execute.return_value = make_scalar_result(campaign)
        data = CampaignUpdate(name="Updated Campaign")

        service = TenDLCService(mock_db)
        await service.update_campaign(TENANT_ACME_ID, campaign.id, data)
        assert campaign.name == "Updated Campaign"

    async def test_cannot_update_pending(self, mock_db):
        campaign = _make_campaign(status="pending")
        mock_db.execute.return_value = make_scalar_result(campaign)
        service = TenDLCService(mock_db)
        with pytest.raises(ValueError, match="Cannot update campaign"):
            await service.update_campaign(
                TENANT_ACME_ID, campaign.id, CampaignUpdate(name="X")
            )


# ── Register Campaign ────────────────────────────────────────────────────


class TestRegisterCampaign:
    @patch("new_phone.sms.factory.get_tenant_default_provider")
    async def test_success(self, mock_get_provider, mock_db):
        brand = _make_brand(status="approved", provider_brand_id="BRAND_1")
        campaign = _make_campaign(status="draft", brand_id=brand.id)

        # get_campaign, then get_brand
        mock_db.execute.side_effect = [
            make_scalar_result(campaign),
            make_scalar_result(brand),
        ]

        mock_config = MagicMock()
        mock_provider = MagicMock()
        mock_provider.register_campaign = AsyncMock(return_value={"campaign_id": "CAMP_1"})
        mock_get_provider.return_value = (mock_config, mock_provider)

        service = TenDLCService(mock_db)
        await service.register_campaign(TENANT_ACME_ID, campaign.id)
        assert campaign.status == "pending"
        assert campaign.provider_campaign_id == "CAMP_1"

    async def test_brand_not_approved_raises(self, mock_db):
        brand = _make_brand(status="pending")
        campaign = _make_campaign(status="draft", brand_id=brand.id)

        mock_db.execute.side_effect = [
            make_scalar_result(campaign),
            make_scalar_result(brand),
        ]
        service = TenDLCService(mock_db)
        with pytest.raises(ValueError, match="brand must be approved"):
            await service.register_campaign(TENANT_ACME_ID, campaign.id)


# ── Compliance Documents ─────────────────────────────────────────────────


class TestUploadComplianceDoc:
    async def test_success(self, mock_db):
        brand = _make_brand()
        mock_db.execute.return_value = make_scalar_result(brand)

        service = TenDLCService(mock_db)
        await service.upload_compliance_doc(
            TENANT_ACME_ID, brand.id,
            document_type="privacy_policy",
            file_path="/uploads/privacy.pdf",
            original_filename="privacy.pdf",
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    async def test_brand_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = TenDLCService(mock_db)
        with pytest.raises(ValueError, match="Brand not found"):
            await service.upload_compliance_doc(
                TENANT_ACME_ID, uuid.uuid4(),
                "privacy_policy", "/path", "file.pdf"
            )


class TestListComplianceDocs:
    async def test_returns_docs(self, mock_db):
        doc = MagicMock()
        mock_db.execute.return_value = make_scalars_result([doc])

        service = TenDLCService(mock_db)
        result = await service.list_compliance_docs(TENANT_ACME_ID, uuid.uuid4())
        assert len(result) == 1
