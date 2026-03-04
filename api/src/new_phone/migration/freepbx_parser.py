"""Parse FreePBX backup (MySQL dump) into a normalized MigrationData structure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class MigrationData:
    """Normalized migration data extracted from any PBX platform."""

    extensions: list[dict] = field(default_factory=list)
    ring_groups: list[dict] = field(default_factory=list)
    ivr_menus: list[dict] = field(default_factory=list)
    dids: list[dict] = field(default_factory=list)
    routes: list[dict] = field(default_factory=list)
    time_conditions: list[dict] = field(default_factory=list)


class FreePBXParser:
    """Parse a FreePBX MySQL-dump backup into MigrationData."""

    # Tables we care about and the method that handles each.
    _TABLE_HANDLERS: ClassVar[dict[str, str]] = {
        "sip": "_parse_sip_rows",
        "users": "_parse_users_rows",
        "ringgroups": "_parse_ringgroups_rows",
        "ivr_details": "_parse_ivr_rows",
        "incoming": "_parse_incoming_rows",
        "outbound_routes": "_parse_outbound_routes_rows",
        "outbound_route_patterns": "_parse_outbound_route_patterns_rows",
        "timegroups_details": "_parse_timegroups_rows",
    }

    # Regex to match INSERT INTO statements.
    _INSERT_RE = re.compile(
        r"INSERT\s+INTO\s+[`'\"]?(\w+)[`'\"]?\s+"
        r"(?:\([^)]*\)\s+)?VALUES\s*(.+?);",
        re.IGNORECASE | re.DOTALL,
    )

    # Regex to split individual value tuples from a VALUES clause.
    _TUPLE_RE = re.compile(r"\(([^)]*)\)")

    def parse_backup(self, file_content: bytes) -> MigrationData:
        """Parse a FreePBX MySQL dump and return normalised MigrationData."""
        text = file_content.decode("utf-8", errors="replace")
        data = MigrationData()

        # Collect raw rows keyed by table name.
        raw: dict[str, list[list[str]]] = {}
        for match in self._INSERT_RE.finditer(text):
            table = match.group(1).lower()
            if table not in self._TABLE_HANDLERS:
                continue
            values_clause = match.group(2)
            for tup in self._TUPLE_RE.finditer(values_clause):
                row = self._split_row(tup.group(1))
                raw.setdefault(table, []).append(row)

        # Merge SIP device settings with user entries.
        sip_devices = self._index_sip(raw.get("sip", []))
        data.extensions = self._build_extensions(
            raw.get("users", []), sip_devices
        )
        data.ring_groups = self._build_ring_groups(raw.get("ringgroups", []))
        data.ivr_menus = self._build_ivr_menus(raw.get("ivr_details", []))
        data.dids = self._build_dids(raw.get("incoming", []))
        data.routes = self._build_routes(
            raw.get("outbound_routes", []),
            raw.get("outbound_route_patterns", []),
        )
        data.time_conditions = self._build_time_conditions(
            raw.get("timegroups_details", [])
        )

        return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_row(values_str: str) -> list[str]:
        """Split a comma-separated VALUES tuple into individual values."""
        parts: list[str] = []
        current: list[str] = []
        in_quote = False
        quote_char = ""
        for ch in values_str:
            if in_quote:
                if ch == quote_char:
                    in_quote = False
                else:
                    current.append(ch)
            elif ch in ("'", '"'):
                in_quote = True
                quote_char = ch
            elif ch == ",":
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
        parts.append("".join(current).strip())
        return parts

    @staticmethod
    def _clean(value: str) -> str:
        return value.strip().strip("'\"")

    # -- SIP table ---------------------------------------------------

    @staticmethod
    def _index_sip(rows: list[list[str]]) -> dict[str, dict[str, str]]:
        """Index SIP key/value rows by extension id."""
        devices: dict[str, dict[str, str]] = {}
        for row in rows:
            if len(row) < 4:
                continue
            ext_id = row[0]
            keyword = row[1]
            value = row[2]
            devices.setdefault(ext_id, {})[keyword] = value
        return devices

    # -- Extensions ---------------------------------------------------

    @staticmethod
    def _build_extensions(
        user_rows: list[list[str]],
        sip_devices: dict[str, dict[str, str]],
    ) -> list[dict]:
        extensions: list[dict] = []
        for row in user_rows:
            if len(row) < 2:
                continue
            ext_num = row[0]
            name = row[1] if len(row) > 1 else ""
            sip = sip_devices.get(ext_num, {})
            extensions.append({
                "extension": ext_num,
                "name": name,
                "context": sip.get("context", "from-internal"),
                "secret": sip.get("secret", ""),
                "callerid": sip.get("callerid", name),
            })
        return extensions

    # -- Ring Groups --------------------------------------------------

    @staticmethod
    def _build_ring_groups(rows: list[list[str]]) -> list[dict]:
        groups: list[dict] = []
        for row in rows:
            if len(row) < 4:
                continue
            groups.append({
                "group_number": row[0],
                "description": row[1],
                "strategy": row[2],
                "members": row[3].split("-") if row[3] else [],
            })
        return groups

    # -- IVR Menus ----------------------------------------------------

    @staticmethod
    def _build_ivr_menus(rows: list[list[str]]) -> list[dict]:
        menus: list[dict] = []
        for row in rows:
            if len(row) < 3:
                continue
            menus.append({
                "ivr_id": row[0],
                "name": row[1],
                "timeout": row[2] if len(row) > 2 else "10",
            })
        return menus

    # -- DIDs / Incoming Routes ---------------------------------------

    @staticmethod
    def _build_dids(rows: list[list[str]]) -> list[dict]:
        dids: list[dict] = []
        for row in rows:
            if len(row) < 3:
                continue
            dids.append({
                "did_number": row[0],
                "destination": row[1],
                "description": row[2] if len(row) > 2 else "",
            })
        return dids

    # -- Outbound Routes ----------------------------------------------

    @staticmethod
    def _build_routes(
        route_rows: list[list[str]],
        pattern_rows: list[list[str]],
    ) -> list[dict]:
        routes: list[dict] = []
        patterns_by_route: dict[str, list[str]] = {}
        for row in pattern_rows:
            if len(row) >= 2:
                patterns_by_route.setdefault(row[0], []).append(row[1])
        for row in route_rows:
            if len(row) < 2:
                continue
            route_id = row[0]
            routes.append({
                "route_id": route_id,
                "name": row[1],
                "patterns": patterns_by_route.get(route_id, []),
            })
        return routes

    # -- Time Conditions / Timegroups ---------------------------------

    @staticmethod
    def _build_time_conditions(rows: list[list[str]]) -> list[dict]:
        conditions: list[dict] = []
        for row in rows:
            if len(row) < 2:
                continue
            conditions.append({
                "timegroup_id": row[0],
                "time": row[1],
            })
        return conditions
