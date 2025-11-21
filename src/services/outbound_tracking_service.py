from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import structlog

try:
    import gspread  # type: ignore
    from gspread.utils import rowcol_to_a1  # type: ignore
    _GSPREAD_IMPORT_ERROR: Exception | None = None
except ModuleNotFoundError as exc:
    gspread = None  # type: ignore
    rowcol_to_a1 = None  # type: ignore
    _GSPREAD_IMPORT_ERROR = exc

from scripts.service_account_loader import resolve_service_account_path
from src.config import settings

if TYPE_CHECKING:  # pragma: no cover
    import gspread  # type: ignore

OUTBOUND_STATUS_COL = "outbound_status"
OUTBOUND_CALL_ID_COL = "outbound_call_id"
OUTBOUND_LAST_ATTEMPT_COL = "outbound_last_attempt_utc"
OUTBOUND_ERROR_COL = "outbound_error"


class OutboundTrackingService:
    """
    Helper for updating the outbound Google Sheet with call outcomes.
    """

    def __init__(self) -> None:
        if gspread is None or rowcol_to_a1 is None:
            raise RuntimeError(
                "gspread is not installed; outbound tracking requires Google Sheets access."
            ) from _GSPREAD_IMPORT_ERROR
        self.logger = structlog.get_logger(__name__)
        if not settings.google_service_account_json or not settings.google_spreadsheet_id:
            raise RuntimeError("Google Sheets credentials are not configured for outbound tracking.")
        self._sheet: "gspread.Worksheet" | None = None
        self._header_map: dict[str, int] | None = None

    def _get_sheet(self) -> gspread.Worksheet:
        if self._sheet is None:
            resolved = resolve_service_account_path(settings.google_service_account_json)
            client = gspread.service_account(filename=resolved)
            spreadsheet = client.open_by_key(settings.google_spreadsheet_id)
            worksheet_title = settings.google_worksheet_title or "2025"
            self._sheet = spreadsheet.worksheet(worksheet_title)
        return self._sheet

    def _ensure_header_map(self) -> dict[str, int]:
        if self._header_map is None:
            sheet = self._get_sheet()
            header_row = [header.strip() for header in sheet.row_values(1)]
            self._header_map = {header: idx + 1 for idx, header in enumerate(header_row)}
        return self._header_map

    def update_row(
        self,
        row_index: int,
        status: str,
        call_id: str | None = None,
        error: str | None = None,
        last_attempt_iso: str | None = None,
    ) -> None:
        sheet = self._get_sheet()
        header_map = self._ensure_header_map()

        updates: list[dict[str, list[list[str]]]] = []

        def add_update(header: str, value: str | None) -> None:
            if header not in header_map:
                self.logger.warning(
                    "header_not_found",
                    header=header,
                    available_headers=list(header_map.keys()),
                    row_index=row_index
                )
                return
            cell = rowcol_to_a1(row_index, header_map[header])
            updates.append({"range": cell, "values": [[value or ""]]})

        add_update(OUTBOUND_STATUS_COL, status)
        add_update(OUTBOUND_CALL_ID_COL, call_id)
        add_update(OUTBOUND_ERROR_COL, error)

        if last_attempt_iso is None:
            last_attempt_iso = datetime.now(timezone.utc).isoformat()
        add_update(OUTBOUND_LAST_ATTEMPT_COL, last_attempt_iso)

        if not updates:
            self.logger.warning("outbound_tracking_no_updates", row=row_index)
            return

        sheet.batch_update(updates)
        self.logger.info(
            "outbound_tracking_updated",
            row=row_index,
            status=status,
            call_id=call_id,
        )


