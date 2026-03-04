"""Parse 3CX XML configuration export into a normalized MigrationData structure."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from new_phone.migration.freepbx_parser import MigrationData


class ThreeCXParser:
    """Parse a 3CX XML config export and return MigrationData."""

    def parse_xml(self, file_content: bytes) -> MigrationData:
        """Parse 3CX XML export bytes and return normalised MigrationData."""
        root = ET.fromstring(file_content)
        data = MigrationData()

        data.extensions = self._parse_extensions(root)
        data.ring_groups = self._parse_ring_groups(root)
        data.ivr_menus = self._parse_ivr_menus(root)
        data.dids = self._parse_dids(root)
        data.routes = self._parse_routes(root)
        data.time_conditions = self._parse_time_conditions(root)

        return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _text(el: ET.Element | None, default: str = "") -> str:
        """Safely extract text from an element."""
        if el is None or el.text is None:
            return default
        return el.text.strip()

    def _parse_extensions(self, root: ET.Element) -> list[dict]:
        extensions: list[dict] = []
        for ext in root.iter("Extension"):
            extensions.append({
                "extension": self._text(ext.find("Number")),
                "name": self._text(ext.find("FirstName"))
                + " "
                + self._text(ext.find("LastName")),
                "email": self._text(ext.find("EmailAddress")),
                "did": self._text(ext.find("DID")),
                "auth_id": self._text(ext.find("AuthID")),
            })
        return extensions

    def _parse_ring_groups(self, root: ET.Element) -> list[dict]:
        groups: list[dict] = []
        for rg in root.iter("RingGroup"):
            members: list[str] = []
            for member in rg.iter("Member"):
                num = self._text(member.find("Number"))
                if num:
                    members.append(num)
            groups.append({
                "group_number": self._text(rg.find("Number")),
                "name": self._text(rg.find("Name")),
                "strategy": self._text(rg.find("RingStrategy"), "simultaneous"),
                "ring_time": self._text(rg.find("RingTime"), "25"),
                "members": members,
            })
        return groups

    def _parse_ivr_menus(self, root: ET.Element) -> list[dict]:
        menus: list[dict] = []
        for ivr in root.iter("IVR"):
            options: list[dict] = []
            for opt in ivr.iter("Option"):
                options.append({
                    "digit": self._text(opt.find("Digit")),
                    "destination": self._text(opt.find("Destination")),
                })
            menus.append({
                "name": self._text(ivr.find("Name")),
                "timeout": self._text(ivr.find("Timeout"), "10"),
                "options": options,
            })
        return menus

    def _parse_dids(self, root: ET.Element) -> list[dict]:
        dids: list[dict] = []
        for did in root.iter("DID"):
            dids.append({
                "did_number": self._text(did.find("Number")),
                "destination": self._text(did.find("Destination")),
                "description": self._text(did.find("Name")),
            })
        return dids

    def _parse_routes(self, root: ET.Element) -> list[dict]:
        routes: list[dict] = []
        for route in root.iter("OutboundRule"):
            patterns: list[str] = []
            for pat in route.iter("Pattern"):
                p = self._text(pat)
                if p:
                    patterns.append(p)
            routes.append({
                "name": self._text(route.find("Name")),
                "prefix": self._text(route.find("Prefix")),
                "patterns": patterns,
            })
        return routes

    def _parse_time_conditions(self, root: ET.Element) -> list[dict]:
        conditions: list[dict] = []
        for tc in root.iter("TimeCondition"):
            conditions.append({
                "name": self._text(tc.find("Name")),
                "start_time": self._text(tc.find("StartTime")),
                "end_time": self._text(tc.find("EndTime")),
                "days": self._text(tc.find("Days")),
            })
        return conditions
