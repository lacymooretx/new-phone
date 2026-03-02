"""FreeSWITCH configuration sync — notifies FS when API data changes.

All operations are best-effort: if FreeSWITCH is unreachable, the API
operation still succeeds. Config changes will take effect on FS restart
or next xml_curl cache expiry.
"""

from __future__ import annotations

import structlog

from new_phone.services.freeswitch_service import FreeSwitchService

logger = structlog.get_logger()


class ConfigSync:
    """Coordinates FreeSWITCH cache/profile updates after API changes."""

    def __init__(self, fs_service: FreeSwitchService):
        self.fs = fs_service

    async def notify_directory_change(self) -> None:
        """Flush xml_curl cache after extension/user changes."""
        await self.fs.flush_xml_cache()

    async def notify_dialplan_change(self) -> None:
        """Flush xml_curl cache after route/ring group/voicemail changes."""
        await self.fs.flush_xml_cache()

    async def notify_gateway_change(self, gateway_name: str | None = None) -> None:
        """Kill gateway, flush cache, and rescan after trunk changes."""
        if gateway_name:
            await self.fs.kill_gateway(gateway_name)
        await self.fs.flush_xml_cache()
        await self.fs.sofia_profile_rescan()

    async def notify_gateway_create(self) -> None:
        """Flush cache and rescan after new trunk creation."""
        await self.fs.flush_xml_cache()
        await self.fs.sofia_profile_rescan()

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
