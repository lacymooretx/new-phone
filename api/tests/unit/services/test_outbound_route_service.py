"""Tests for new_phone.services.outbound_route_service — outbound route CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.outbound_route_service import OutboundRouteService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_route(**overrides):
    route = MagicMock()
    route.id = overrides.get("id", uuid.uuid4())
    route.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    route.name = overrides.get("name", "Outbound Default")
    route.is_active = overrides.get("is_active", True)
    route.deactivated_at = overrides.get("deactivated_at")
    return route


class TestListOutboundRoutes:
    async def test_returns_list(self, mock_db):
        r1 = _make_route(name="Default")
        r2 = _make_route(name="Emergency")
        mock_db.execute.return_value = make_scalars_result([r1, r2])

        service = OutboundRouteService(mock_db)
        result = await service.list_outbound_routes(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = OutboundRouteService(mock_db)
        result = await service.list_outbound_routes(TENANT_ACME_ID)
        assert result == []


class TestGetOutboundRoute:
    async def test_found(self, mock_db):
        route = _make_route(name="Default")
        mock_db.execute.return_value = make_scalar_result(route)
        service = OutboundRouteService(mock_db)
        result = await service.get_outbound_route(TENANT_ACME_ID, route.id)
        assert result.name == "Default"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = OutboundRouteService(mock_db)
        result = await service.get_outbound_route(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateOutboundRoute:
    async def test_success(self, mock_db):
        from new_phone.schemas.outbound_route import OutboundRouteCreate

        trunk_id = uuid.uuid4()
        service = OutboundRouteService(mock_db)
        data = OutboundRouteCreate(
            name="New Route",
            dial_pattern="^1?([2-9]\\d{9})$",
            priority=1,
            trunk_ids=[trunk_id],
        )
        await service.create_outbound_route(TENANT_ACME_ID, data)
        # Route + 1 trunk assignment = 2 add calls
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_awaited()


class TestUpdateOutboundRoute:
    async def test_success(self, mock_db):
        from new_phone.schemas.outbound_route import OutboundRouteUpdate

        route = _make_route()
        mock_db.execute.return_value = make_scalar_result(route)
        service = OutboundRouteService(mock_db)
        data = OutboundRouteUpdate(name="Updated")
        await service.update_outbound_route(TENANT_ACME_ID, route.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.outbound_route import OutboundRouteUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = OutboundRouteService(mock_db)
        data = OutboundRouteUpdate(name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_outbound_route(TENANT_ACME_ID, uuid.uuid4(), data)


class TestDeactivateOutboundRoute:
    async def test_success(self, mock_db):
        route = _make_route(is_active=True)
        mock_db.execute.return_value = make_scalar_result(route)
        service = OutboundRouteService(mock_db)
        await service.deactivate_outbound_route(TENANT_ACME_ID, route.id)
        assert route.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = OutboundRouteService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate_outbound_route(TENANT_ACME_ID, uuid.uuid4())
