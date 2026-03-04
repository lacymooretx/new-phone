import asyncio

import structlog

logger = structlog.get_logger()


class FreeSwitchService:
    """FreeSWITCH ESL client for health checks and configuration management.

    Uses raw async sockets for ESL communication.
    """

    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self._connected = False

    async def connect(self) -> None:
        """Test ESL connectivity on startup."""
        try:
            status = await self._send_command("api status")
            if status:
                self._connected = True
                logger.info("freeswitch_connected", host=self.host, port=self.port)
            else:
                logger.warning("freeswitch_no_response", host=self.host)
        except Exception as e:
            self._connected = False
            logger.warning("freeswitch_connection_failed", error=str(e))

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("freeswitch_disconnected")

    async def is_healthy(self) -> dict:
        """Check if FreeSWITCH is reachable."""
        try:
            response = await self._send_command("api status")
            if response:
                self._connected = True
                return {"status": "connected", "healthy": True, "info": response[:200]}
            return {"status": "no_response", "healthy": False}
        except Exception as e:
            self._connected = False
            return {"status": "error", "healthy": False, "error": str(e)}

    async def flush_xml_cache(self) -> bool:
        """Flush the xml_curl cache so FreeSWITCH re-fetches config."""
        try:
            result = await self._send_command("api xml_flush_cache")
            logger.info("freeswitch_xml_cache_flushed", result=result)
            return result is not None
        except Exception as e:
            logger.warning("freeswitch_flush_cache_failed", error=str(e))
            return False

    async def sofia_profile_rescan(self, profile: str = "external") -> bool:
        """Rescan a sofia profile to pick up gateway changes."""
        try:
            result = await self._send_command(f"api sofia profile {profile} rescan")
            logger.info("freeswitch_sofia_rescan", profile=profile, result=result)
            return result is not None
        except Exception as e:
            logger.warning("freeswitch_sofia_rescan_failed", profile=profile, error=str(e))
            return False

    async def kill_gateway(self, gateway_name: str, profile: str = "external") -> bool:
        """Remove a gateway from a sofia profile."""
        try:
            result = await self._send_command(f"api sofia profile {profile} killgw {gateway_name}")
            logger.info("freeswitch_gateway_killed", gateway=gateway_name, result=result)
            return result is not None
        except Exception as e:
            logger.warning("freeswitch_kill_gateway_failed", gateway=gateway_name, error=str(e))
            return False

    async def callcenter_config(self, command: str) -> bool:
        """Send a callcenter_config command to FreeSWITCH."""
        try:
            result = await self._send_command(f"api callcenter_config {command}")
            logger.info("freeswitch_callcenter_config", command=command, result=result)
            return result is not None
        except Exception as e:
            logger.warning("freeswitch_callcenter_config_failed", command=command, error=str(e))
            return False

    async def valet_park_info(self, lot_name: str) -> str | None:
        """Query valet parking lot status from FreeSWITCH."""
        try:
            result = await self._send_command(f"api valet_info {lot_name}")
            logger.info("freeswitch_valet_info", lot=lot_name, result=result)
            return result
        except Exception as e:
            logger.warning("freeswitch_valet_info_failed", lot=lot_name, error=str(e))
            return None

    async def reload_xml(self) -> bool:
        """Reload XML configuration."""
        try:
            result = await self._send_command("api reloadxml")
            logger.info("freeswitch_xml_reloaded", result=result)
            return result is not None
        except Exception as e:
            logger.warning("freeswitch_reload_xml_failed", error=str(e))
            return False

    async def originate_call(
        self, sip_username: str, destination: str, timeout: int = 30
    ) -> str | None:
        """Originate a call: ring user's device, then bridge to destination."""
        command = (
            f"bgapi originate "
            f"{{originate_timeout={timeout}}}user/{sip_username} "
            f"{destination} XML default"
        )
        return await self._send_command(command, timeout=float(timeout + 5))

    async def _send_command(self, command: str, timeout: float = 5.0) -> str | None:
        """Send a single ESL command and return the response body."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=timeout,
            )
        except (TimeoutError, ConnectionRefusedError, OSError):
            return None

        try:
            # Read the initial Content-Type header
            await asyncio.wait_for(self._read_until_blank(reader), timeout=timeout)

            # Authenticate
            writer.write(f"auth {self.password}\n\n".encode())
            await writer.drain()
            auth_response = await asyncio.wait_for(self._read_until_blank(reader), timeout=timeout)
            if "Reply-Text: +OK" not in auth_response:
                return None

            # Send command
            writer.write(f"{command}\n\n".encode())
            await writer.drain()

            # Read response headers
            headers = await asyncio.wait_for(self._read_until_blank(reader), timeout=timeout)

            # Extract Content-Length and read body
            content_length = 0
            for line in headers.split("\n"):
                if line.startswith("Content-Length:"):
                    content_length = int(line.split(":")[1].strip())
                    break

            if content_length > 0:
                body = await asyncio.wait_for(reader.readexactly(content_length), timeout=timeout)
                return body.decode().strip()

            return headers
        finally:
            writer.close()
            await writer.wait_closed()

    async def originate_eavesdrop(
        self, listener_sip_username: str, target_uuid: str, timeout: int = 300
    ) -> str | None:
        """Originate an eavesdrop call: ring listener's device, bridge to target's audio (listen-only)."""
        command = (
            f"bgapi originate "
            f"{{originate_timeout=30,eavesdrop_indicate_failed=true}}"
            f"user/{listener_sip_username} "
            f"&eavesdrop({target_uuid})"
        )
        result = await self._send_command(command, timeout=35.0)
        if result and result.startswith("+OK"):
            # bgapi returns "+OK Job-UUID: <uuid>"
            parts = result.split()
            if len(parts) >= 3:
                return parts[-1]
        return result

    async def show_channels_for_user(self, sip_username: str) -> list[str]:
        """Get active channel UUIDs for a SIP user."""
        result = await self._send_command("api show calls as json")
        if not result:
            return []
        try:
            import json

            data = json.loads(result)
            rows = data.get("rows", [])
            uuids = []
            for row in rows:
                # Check caller fields for the sip_username
                cid_num = row.get("cid_num", "")
                dest = row.get("dest", "")
                name = row.get("name", "")
                if sip_username in (cid_num, dest, name):
                    call_uuid = row.get("uuid", "")
                    if call_uuid:
                        uuids.append(call_uuid)
            return uuids
        except (json.JSONDecodeError, KeyError):
            return []

    async def uuid_kill(self, call_uuid: str) -> bool:
        """Kill (hangup) a specific channel by UUID."""
        try:
            result = await self._send_command(f"api uuid_kill {call_uuid}")
            logger.info("freeswitch_uuid_kill", uuid=call_uuid, result=result)
            return result is not None
        except Exception as e:
            logger.warning("freeswitch_uuid_kill_failed", uuid=call_uuid, error=str(e))
            return False

    @staticmethod
    async def _read_until_blank(reader: asyncio.StreamReader) -> str:
        """Read lines until a blank line (ESL message delimiter)."""
        lines = []
        while True:
            line = await reader.readline()
            decoded = line.decode().rstrip("\n").rstrip("\r")
            if decoded == "":
                break
            lines.append(decoded)
        return "\n".join(lines)
