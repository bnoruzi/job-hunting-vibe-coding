"""Repository abstraction for persisting job records to Google Sheets."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported for type hints only
    from gspread.worksheet import Worksheet
else:  # pragma: no cover - fallback for runtime when gspread isn't installed locally
    Worksheet = Any  # type: ignore


class SheetsRepository:
    """Lightweight wrapper that upserts job rows into a Google Sheet.

    Rows are keyed by job URL (the ``Link`` column). Dynamic metadata and
    enrichment fields are converted into columns automatically and persisted in
    the sheet, enabling reprocessing runs to update previously fetched jobs.
    """

    BASE_HEADER: List[str] = [
        "Fetched At (UTC)",
        "Role",
        "Job Title",
        "Source",
        "Link",
    ]
    ENRICHMENT_KEYS: Tuple[str, ...] = (
        "ai_fit_score",
        "ai_summary",
        "ai_outreach_angle",
    )

    def __init__(self, sheet: "Worksheet") -> None:
        self.sheet = sheet
        self.header: List[str] = []
        self.key_to_header: Dict[str, str] = {}
        self.rows_by_link: Dict[str, Tuple[int, List[Any]]] = {}
        self.row_count: int = 0
        self._initialize()
        self._ensure_dynamic_keys(self.ENRICHMENT_KEYS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def upsert_job(
        self,
        *,
        fetched_at: Any,
        role: Any,
        title: Any,
        source: Any,
        link: str,
        metadata: Optional[Mapping[str, Any]] = None,
        enrichment: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        """Insert or update a job row by URL.

        Args:
            fetched_at: Timestamp indicating when the job was fetched.
            role: Role name used for the search.
            title: Job title returned by the provider.
            source: Provider/source label.
            link: Unique job URL used as the primary key.
            metadata: Provider metadata to persist as additional columns.
            enrichment: Optional enrichment payload to persist alongside
                metadata.

        Returns:
            ``True`` if the call created a new row, ``False`` if the existing
            row was updated.
        """

        if not link:
            raise ValueError("A job link is required to upsert a record.")

        dynamic_values = self._merge_dynamic_fields(metadata, enrichment)
        self._ensure_dynamic_keys(dynamic_values.keys())

        base_values = {
            "Fetched At (UTC)": fetched_at or "",
            "Role": role or "",
            "Job Title": title or "",
            "Source": source or "",
            "Link": link,
        }
        row_data = self._compose_row(base_values, dynamic_values)

        existing = self.rows_by_link.get(link)
        if existing:
            row_index, _ = existing
            self.sheet.update(f"A{row_index}", [row_data])
            self.rows_by_link[link] = (row_index, row_data)
            return False

        self.sheet.append_row(row_data)
        self.row_count += 1
        row_index = self.row_count
        self.rows_by_link[link] = (row_index, row_data)
        return True

    def has_link(self, link: str) -> bool:
        """Return ``True`` if a row already exists for ``link``."""

        return link in self.rows_by_link

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _initialize(self) -> None:
        existing = self.sheet.get_all_values()
        if not existing:
            self.header = self.BASE_HEADER.copy()
            self.key_to_header = {
                self._header_to_key(column): column for column in self.header
            }
            self.rows_by_link = {}
            self._ensure_header()
            self.row_count = 1
            return

        header_row = existing[0]
        prepared_header = self._prepare_header(header_row)
        self.header = prepared_header
        self.key_to_header = {
            self._header_to_key(column): column for column in self.header
        }
        if self.header != header_row:
            self._ensure_header()

        self.row_count = len(existing)
        self.rows_by_link = {}
        link_index = self.header.index("Link") if "Link" in self.header else -1
        if link_index >= 0:
            for row_number, row in enumerate(existing[1:], start=2):
                link = row[link_index] if len(row) > link_index else ""
                if not link:
                    continue
                normalized_row = list(row) + [""] * (len(self.header) - len(row))
                self.rows_by_link[link] = (row_number, normalized_row)

    def _prepare_header(self, existing_header: List[str]) -> List[str]:
        header = self.BASE_HEADER.copy()
        for column in existing_header:
            if column not in header:
                header.append(column)
        return header

    def _ensure_header(self) -> None:
        self.sheet.update("A1", [self.header])

    def _ensure_dynamic_keys(self, keys: Iterable[str]) -> None:
        added = False
        for key in keys:
            if not key:
                continue
            if key in self.key_to_header:
                continue
            header_label = self._key_to_header(key)
            base_label = header_label
            suffix = 2
            while header_label in self.header:
                header_label = f"{base_label} {suffix}"
                suffix += 1
            self.header.append(header_label)
            self.key_to_header[key] = header_label
            added = True
        if added:
            self._ensure_header()

    def _merge_dynamic_fields(
        self,
        metadata: Optional[Mapping[str, Any]],
        enrichment: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        dynamic: Dict[str, Any] = {}
        for payload in (metadata, enrichment):
            if not payload:
                continue
            for key, value in payload.items():
                normalized_key = self._normalize_key(str(key))
                if not normalized_key:
                    continue
                dynamic[normalized_key] = value
        return dynamic

    def _compose_row(
        self,
        base_values: Mapping[str, Any],
        dynamic_values: Mapping[str, Any],
    ) -> List[Any]:
        row: List[Any] = []
        for column in self.header:
            if column in base_values:
                row.append(base_values.get(column, ""))
            else:
                key = self._header_to_key(column)
                row.append(dynamic_values.get(key, ""))
        return row

    @staticmethod
    def _normalize_key(key: str) -> str:
        normalized = key.strip().lower().replace(" ", "_")
        normalized = normalized.replace("-", "_")
        return normalized

    @staticmethod
    def _header_to_key(header: str) -> str:
        return header.lower().replace(" ", "_")

    @staticmethod
    def _key_to_header(key: str) -> str:
        words = key.replace("-", "_").split("_")
        return " ".join(word.capitalize() for word in words if word)
