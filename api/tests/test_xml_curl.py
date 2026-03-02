"""Integration tests for FreeSWITCH xml_curl endpoints.

These tests require the API to be running against a seeded database.
"""

from xml.etree.ElementTree import fromstring

import pytest
from httpx import AsyncClient

from tests.conftest import API_BASE_URL


@pytest.fixture
async def xml_client() -> AsyncClient:
    """Client for xml_curl endpoints (no auth needed)."""
    async with AsyncClient(base_url=API_BASE_URL) as ac:
        yield ac


class TestDirectoryEndpoint:
    """POST /freeswitch/directory tests."""

    async def test_directory_valid_extension(self, xml_client: AsyncClient, msp_admin_token: str):
        """After resync, a valid extension returns directory XML."""
        # First, resync credentials to populate encrypted passwords
        async with AsyncClient(base_url=API_BASE_URL) as c:
            resp = await c.post(
                "/api/v1/admin/resync-credentials",
                headers={"Authorization": f"Bearer {msp_admin_token}"},
            )
            if resp.status_code != 200:
                pytest.skip("Resync failed — seed data may not be loaded")

        # Now test directory lookup
        resp = await xml_client.post(
            "/freeswitch/directory",
            data={
                "section": "directory",
                "action": "sip_auth",
                "sip_auth_username": "100",
                "domain": "acme.sip.local",
            },
        )
        assert resp.status_code == 200
        assert "text/xml" in resp.headers["content-type"]

        root = fromstring(resp.text)
        assert root.attrib["type"] == "freeswitch/xml"

        user = root.find(".//user")
        assert user is not None
        assert user.attrib["id"] == "100"

        # Should have a password param
        params = {p.attrib["name"]: p.attrib["value"] for p in user.findall(".//param")}
        assert "password" in params
        assert len(params["password"]) > 0

    async def test_directory_unknown_extension(self, xml_client: AsyncClient):
        """Unknown extension returns not-found XML."""
        resp = await xml_client.post(
            "/freeswitch/directory",
            data={
                "section": "directory",
                "action": "sip_auth",
                "sip_auth_username": "999",
                "domain": "acme.sip.local",
            },
        )
        assert resp.status_code == 200
        assert 'status="not found"' in resp.text

    async def test_directory_unknown_domain(self, xml_client: AsyncClient):
        """Unknown domain returns not-found XML."""
        resp = await xml_client.post(
            "/freeswitch/directory",
            data={
                "section": "directory",
                "sip_auth_username": "100",
                "domain": "nonexistent.sip.local",
            },
        )
        assert resp.status_code == 200
        assert 'status="not found"' in resp.text

    async def test_directory_empty_params(self, xml_client: AsyncClient):
        """Missing username/domain returns not-found XML."""
        resp = await xml_client.post(
            "/freeswitch/directory",
            data={"section": "directory"},
        )
        assert resp.status_code == 200
        assert 'status="not found"' in resp.text

    async def test_directory_tenant_isolation(self, xml_client: AsyncClient):
        """Extension from one tenant's domain can't be found in another's."""
        resp = await xml_client.post(
            "/freeswitch/directory",
            data={
                "section": "directory",
                "sip_auth_username": "100",
                "domain": "msp.sip.local",  # ext 100 belongs to acme, not msp
            },
        )
        assert resp.status_code == 200
        assert 'status="not found"' in resp.text


class TestDialplanEndpoint:
    """POST /freeswitch/dialplan tests."""

    async def test_dialplan_valid_context(self, xml_client: AsyncClient):
        """Valid tenant context returns dialplan XML with feature codes."""
        resp = await xml_client.post(
            "/freeswitch/dialplan",
            data={
                "section": "dialplan",
                "Caller-Context": "acme",
                "Destination-Number": "100",
            },
        )
        assert resp.status_code == 200
        assert "text/xml" in resp.headers["content-type"]

        root = fromstring(resp.text)
        context = root.find(".//context")
        assert context is not None
        assert context.attrib["name"] == "acme"

        # Should have feature codes
        ext_names = [e.attrib["name"] for e in context.findall("extension")]
        assert "check-voicemail" in ext_names
        assert "dnd-on" in ext_names
        assert "dnd-off" in ext_names

    async def test_dialplan_has_local_extensions(self, xml_client: AsyncClient):
        """Dialplan includes local extension entries from seed data."""
        resp = await xml_client.post(
            "/freeswitch/dialplan",
            data={
                "section": "dialplan",
                "Caller-Context": "acme",
                "Destination-Number": "100",
            },
        )
        root = fromstring(resp.text)
        ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
        assert "local-100" in ext_names
        assert "local-101" in ext_names
        assert "local-102" in ext_names

    async def test_dialplan_has_ring_group(self, xml_client: AsyncClient):
        """Dialplan includes ring group from seed data."""
        resp = await xml_client.post(
            "/freeswitch/dialplan",
            data={
                "section": "dialplan",
                "Caller-Context": "acme",
            },
        )
        root = fromstring(resp.text)
        ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
        assert "ring-group-*601" in ext_names

    async def test_dialplan_has_outbound_route(self, xml_client: AsyncClient):
        """Dialplan includes outbound route from seed data."""
        resp = await xml_client.post(
            "/freeswitch/dialplan",
            data={
                "section": "dialplan",
                "Caller-Context": "acme",
            },
        )
        root = fromstring(resp.text)
        ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
        # Should have at least one outbound route
        outbound = [n for n in ext_names if n.startswith("outbound-")]
        assert len(outbound) > 0

    async def test_dialplan_unknown_context(self, xml_client: AsyncClient):
        """Unknown context returns not-found XML."""
        resp = await xml_client.post(
            "/freeswitch/dialplan",
            data={
                "section": "dialplan",
                "Caller-Context": "nonexistent",
            },
        )
        assert resp.status_code == 200
        assert 'status="not found"' in resp.text

    async def test_dialplan_empty_context(self, xml_client: AsyncClient):
        """Empty context returns not-found XML."""
        resp = await xml_client.post(
            "/freeswitch/dialplan",
            data={"section": "dialplan"},
        )
        assert resp.status_code == 200
        assert 'status="not found"' in resp.text


class TestConfigurationEndpoint:
    """POST /freeswitch/configuration tests."""

    async def test_configuration_sofia_conf(self, xml_client: AsyncClient):
        """sofia.conf request returns gateway config."""
        resp = await xml_client.post(
            "/freeswitch/configuration",
            data={
                "section": "configuration",
                "key_value": "sofia.conf",
            },
        )
        assert resp.status_code == 200
        assert "text/xml" in resp.headers["content-type"]

        root = fromstring(resp.text)
        config = root.find(".//configuration")
        assert config is not None
        assert config.attrib["name"] == "sofia.conf"

    async def test_configuration_unknown_key(self, xml_client: AsyncClient):
        """Non-sofia config request returns not-found."""
        resp = await xml_client.post(
            "/freeswitch/configuration",
            data={
                "section": "configuration",
                "key_value": "voicemail.conf",
            },
        )
        assert resp.status_code == 200
        assert 'status="not found"' in resp.text


class TestAdminResync:
    """POST /api/v1/admin/resync-credentials tests."""

    async def test_resync_requires_msp_admin(self, client: AsyncClient, acme_admin_token: str):
        """Non-MSP admin gets 403."""
        resp = await client.post(
            "/api/v1/admin/resync-credentials",
            headers={"Authorization": f"Bearer {acme_admin_token}"},
        )
        assert resp.status_code == 403

    async def test_resync_success(self, client: AsyncClient, msp_admin_token: str):
        """MSP admin can resync credentials."""
        resp = await client.post(
            "/api/v1/admin/resync-credentials",
            headers={"Authorization": f"Bearer {msp_admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "extensions_updated" in data
        assert "voicemail_boxes_updated" in data
