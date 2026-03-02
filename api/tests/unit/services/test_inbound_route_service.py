"""Tests for new_phone.services.inbound_route_service — inbound route CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.inbound_route_service import InboundRouteService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_route(**overrides):
    route = MagicMock()
    route.id = overrides.get("id", uuid.uuid4())
    route.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    route.name = overrides.get("name", "Main Route")
    route.is_active = overrides.get("is_active", True)
    route.deactivated_at = overrides.get("deactivated_at")
    return route


class TestListInboundRoutes:
    async def test_returns_list(self, mock_db):
        r1 = _make_route(name="Main")
        r2 = _make_route(name="After Hours")
        mock_db.execute.return_value = make_scalars_result([r1, r2])

        service = InboundRouteService(mock_db)
        result = await service.list_inbound_routes(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = InboundRouteService(mock_db)
        result = await service.list_inbound_routes(TENANT_ACME_ID)
        assert result == []


class TestGetInboundRoute:
    async def test_found(self, mock_db):
        route = _make_route(name="Main")
        mock_db.execute.return_value = make_scalar_result(route)
        service = InboundRouteService(mock_db)
        result = await service.get_inbound_route(TENANT_ACME_ID, route.id)
        assert result.name == "Main"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = InboundRouteService(mock_db)
        result = await service.get_inbound_route(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateInboundRoute:
    async def test_success(self, mock_db):
        from new_phone.schemas.inbound_route import InboundRouteCreate

        service = InboundRouteService(mock_db)
        data = InboundRouteCreate(
            name="New Route",
            destination_type="extension",
            destination_id=uuid.uuid4(),
        )
        await service.create_inbound_route(TENANT_ACME_ID, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()


class TestUpdateInboundRoute:
    async def test_success(self, mock_db):
        from new_phone.schemas.inbound_route import InboundRouteUpdate

        route = _make_route()
        mock_db.execute.return_value = make_scalar_result(route)
        service = InboundRouteService(mock_db)
        data = InboundRouteUpdate(name="Updated Route")
        await service.update_inbound_route(TENANT_ACME_ID, route.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.inbound_route import InboundRouteUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = InboundRouteService(mock_db)
        data = InboundRouteUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_inbound_route(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateInboundRoute:
    async def test_success(self, mock_db):
        route = _make_route(is_active=True)
        mock_db.execute.return_value = make_scalar_result(route)
        service = InboundRouteService(mock_db)
        await service.deactivate_inbound_route(TENANT_ACME_ID, route.id)
        assert route.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = InboundRouteService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_inbound_route(TENANT_ACME_ID, uuid.uuid4())
