"""CSV-based bulk import for extensions and DIDs."""

from __future__ import annotations

import csv
import io
import re
from typing import ClassVar

_E164_RE = re.compile(r"^\+?\d{7,15}$")
_EXT_RE = re.compile(r"^\d{2,6}$")


class CSVImporter:
    """Parse and validate CSV files for bulk extension / DID imports."""

    # Required columns per entity type.
    _REQUIRED_COLUMNS: ClassVar[dict[str, set[str]]] = {
        "extension": {"extension", "name"},
        "did": {"did_number"},
    }

    def parse_extensions_csv(self, content: str) -> list[dict]:
        """Parse a CSV string of extensions into a list of dicts.

        Expected columns (minimum): extension, name
        Optional columns: email, voicemail_enabled, caller_id
        """
        return self._parse_csv(content)

    def parse_dids_csv(self, content: str) -> list[dict]:
        """Parse a CSV string of DIDs into a list of dicts.

        Expected columns (minimum): did_number
        Optional columns: description, destination, destination_type
        """
        return self._parse_csv(content)

    def validate_import_data(
        self, data: list[dict], entity_type: str
    ) -> list[str]:
        """Validate parsed CSV data and return a list of error strings.

        Returns an empty list when all rows are valid.
        """
        errors: list[str] = []
        required = self._REQUIRED_COLUMNS.get(entity_type)
        if required is None:
            errors.append(f"Unknown entity type: {entity_type}")
            return errors

        if not data:
            errors.append("No data rows found in CSV")
            return errors

        # Check that required columns exist in the first row.
        first_keys = set(data[0].keys())
        missing_cols = required - first_keys
        if missing_cols:
            errors.append(
                f"Missing required columns: {', '.join(sorted(missing_cols))}"
            )
            return errors

        seen_values: set[str] = set()

        for idx, row in enumerate(data, start=1):
            # Check required fields have values.
            for col in required:
                value = row.get(col, "").strip()
                if not value:
                    errors.append(f"Row {idx}: missing required value for '{col}'")

            if entity_type == "extension":
                ext = row.get("extension", "").strip()
                if ext and not _EXT_RE.match(ext):
                    errors.append(
                        f"Row {idx}: invalid extension number '{ext}' "
                        "(must be 2-6 digits)"
                    )
                if ext in seen_values:
                    errors.append(f"Row {idx}: duplicate extension '{ext}'")
                seen_values.add(ext)

            elif entity_type == "did":
                did = row.get("did_number", "").strip()
                if did and not _E164_RE.match(did):
                    errors.append(
                        f"Row {idx}: invalid DID number '{did}' "
                        "(expected E.164 format)"
                    )
                if did in seen_values:
                    errors.append(f"Row {idx}: duplicate DID '{did}'")
                seen_values.add(did)

        return errors

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_csv(content: str) -> list[dict]:
        reader = csv.DictReader(io.StringIO(content))
        return [
            {k.strip().lower(): v.strip() for k, v in row.items() if k}
            for row in reader
        ]
