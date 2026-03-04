"""FreeSWITCH configuration sync — notifies FS when API data changes.

All operations are best-effort: if FreeSWITCH is unreachable, the API
operation still succeeds. Config changes will take effect on FS restart
or next xml_curl cache expiry.

Gateway XML files are written to a shared volume (/gateways/) that the
FreeSWITCH external profile includes via X-PRE-PROCESS. Changes are
picked up via `reloadxml` + `sofia profile external rescan`.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from new_phone.services.freeswitch_service import FreeSwitchService

logger = structlog.get_logger()

GATEWAY_DIR = Path("/gateways")


class ConfigSync:
    """Coordinates FreeSWITCH cache/profile updates after API changes."""

    def __init__(self, fs_service: FreeSwitchService, gateway_dir: Path | None = None):
        self.fs = fs_service
        self.gateway_dir = gateway_dir or GATEWAY_DIR

    # --- Gateway file I/O ---

    def write_gateway_file(self, gw_name: str, xml_content: str) -> None:
        """Write a gateway XML file to the shared volume."""
        self.gateway_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.gateway_dir / f"{gw_name}.xml"
        filepath.write_text(xml_content)
        logger.info("gateway_file_written", path=str(filepath))

    def remove_gateway_file(self, gw_name: str) -> None:
        """Remove a gateway XML file from the shared volume."""
        filepath = self.gateway_dir / f"{gw_name}.xml"
        if filepath.exists():
            filepath.unlink()
            logger.info("gateway_file_removed", path=str(filepath))

    # --- Gateway lifecycle notifications ---

    async def notify_gateway_create(
        self, gw_name: str | None = None, xml_content: str | None = None
    ) -> None:
        """Write gateway file, flush cache, and rescan after new trunk creation."""
        if gw_name and xml_content:
            self.write_gateway_file(gw_name, xml_content)
        await self.fs.reload_xml()
        await self.fs.sofia_profile_rescan()

    async def notify_gateway_change(
        self,
        old_gw_name: str | None = None,
        new_gw_name: str | None = None,
        xml_content: str | None = None,
    ) -> None:
        """Kill old gateway, update file, reloadxml, and rescan after trunk changes."""
        if old_gw_name:
            await self.fs.kill_gateway(old_gw_name)
            self.remove_gateway_file(old_gw_name)
        if new_gw_name and xml_content:
            self.write_gateway_file(new_gw_name, xml_content)
        await self.fs.reload_xml()
        await self.fs.sofia_profile_rescan()

    async def notify_gateway_delete(self, gw_name: str) -> None:
        """Kill gateway, remove file, and reloadxml after trunk deletion."""
        await self.fs.kill_gateway(gw_name)
        self.remove_gateway_file(gw_name)
        await self.fs.reload_xml()

    async def sync_all_gateways(
        self,
        trunks: list,
        tenants: dict,
        passwords: dict,
    ) -> None:
        """Full gateway sync — write all files, remove stale ones, rescan.

        Called on API startup to ensure gateway files match the database.
        """
        from new_phone.freeswitch.xml_builder import build_gateway_file, gateway_fs_name

        self.gateway_dir.mkdir(parents=True, exist_ok=True)
        expected_files: set[str] = set()

        for trunk in trunks:
            if not trunk.is_active:
                continue
            tenant = tenants.get(str(trunk.tenant_id))
            if not tenant or not trunk.host:
                continue
            gw_name = gateway_fs_name(tenant.slug, trunk.name)
            password = passwords.get(str(trunk.id), "")
            xml = build_gateway_file(trunk, tenant, password)
            if xml:
                self.write_gateway_file(gw_name, xml)
                expected_files.add(f"{gw_name}.xml")

        # Remove stale files
        for f in self.gateway_dir.glob("*.xml"):
            if f.name not in expected_files:
                f.unlink()
                logger.info("gateway_stale_file_removed", path=str(f))

        await self.fs.reload_xml()
        await self.fs.sofia_profile_rescan()
        logger.info("gateway_sync_complete", count=len(expected_files))

    # --- Non-gateway notifications ---

    async def notify_directory_change(self) -> None:
        """Flush xml_curl cache after extension/user changes."""
        await self.fs.flush_xml_cache()

    async def notify_dialplan_change(self) -> None:
        """Flush xml_curl cache after route/ring group/voicemail changes."""
        await self.fs.flush_xml_cache()

    async def notify_queue_change(self, queue_fs_name: str | None = None) -> None:
        """Flush cache and reload callcenter config after queue changes."""
        await self.fs.flush_xml_cache()
        if queue_fs_name:
            await self.fs.callcenter_config(f"queue reload {queue_fs_name}")
        else:
            await self.fs.callcenter_config("queue reload all")

    async def notify_agent_status_change(self, agent_name: str, status: str) -> None:
        """Update agent status in FreeSWITCH callcenter module."""
        await self.fs.callcenter_config(f"agent set status {agent_name} '{status}'")

    async def notify_conference_change(self) -> None:
        """Flush xml_curl cache after conference bridge changes."""
        await self.fs.flush_xml_cache()

    async def notify_paging_change(self) -> None:
        """Flush xml_curl cache after page group changes."""
        await self.fs.flush_xml_cache()

    async def notify_parking_change(self) -> None:
        """Flush xml_curl cache after parking lot changes."""
        await self.fs.flush_xml_cache()

    async def notify_security_change(self) -> None:
        """Flush xml_curl cache after security config changes."""
        await self.fs.flush_xml_cache()

    async def notify_paging_zone_change(self) -> None:
        """Flush xml_curl cache after paging zone changes."""
        await self.fs.flush_xml_cache()

    async def notify_camp_on_change(self) -> None:
        """Flush xml_curl cache after camp-on config changes."""
        await self.fs.flush_xml_cache()
