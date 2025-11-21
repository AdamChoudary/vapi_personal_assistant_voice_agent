"""
Fetch declined-payment CSV attachments from email and load them into Google Sheets.

Workflow:
    1. Connect to the configured IMAP inbox.
    2. Download any CSV attachment matching Batch_*_result.csv.
    3. Parse the latest CSV (by embedded timestamp) into rows.
    4. Replace the target Google Sheet tab with the CSV content.
    5. Mark processed emails as read and persist downloaded files.

Environment variables (required):
    EMAIL_IMAP_SERVER
    EMAIL_ADDRESS
    EMAIL_PASSWORD
    GOOGLE_SERVICE_ACCOUNT_JSON
    GOOGLE_SPREADSHEET_ID

Optional overrides:
    EMAIL_IMAP_PORT (default: 993)
    EMAIL_LOOKBACK_DAYS (default: 10)
    GOOGLE_WORKSHEET_TITLE (default: 2025)
    CSV_DOWNLOAD_DIR (default: data/csv_batches)
    GOOGLE_BATCH_UPDATE_SIZE (default: 5000 rows per request)

Run with:
    uv run python scripts/ingest_email_csv_to_sheet.py
"""

from __future__ import annotations

import asyncio
import csv
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

import gspread
from dotenv import load_dotenv
from gspread.exceptions import APIError

from src.services.email_integration import EmailIntegrationService
from scripts.service_account_loader import resolve_service_account_path


load_dotenv()

REQUIRED_ENV = {
    "EMAIL_IMAP_SERVER",
    "EMAIL_ADDRESS",
    "EMAIL_PASSWORD",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GOOGLE_SPREADSHEET_ID",
}

DEFAULTS = {
    "EMAIL_IMAP_PORT": "993",
    "EMAIL_LOOKBACK_DAYS": "10",
    "GOOGLE_WORKSHEET_TITLE": "2025",
    "CSV_DOWNLOAD_DIR": "data/csv_batches",
    "GOOGLE_BATCH_UPDATE_SIZE": "5000",
}


def get_env() -> dict[str, str]:
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")

    env = {name: os.getenv(name, "") for name in REQUIRED_ENV}  # type: ignore[dict-item]
    for key, default in DEFAULTS.items():
        env[key] = os.getenv(key, default)
    return env  # type: ignore[return-value]


def setup_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    return logging.getLogger("email_csv_ingest")


def as_int(value: str, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def read_csv(file_path: Path) -> list[list[str]]:
    encodings = ("utf-8", "utf-8-sig", "latin-1", "cp1252")
    for encoding in encodings:
        try:
            with file_path.open("r", encoding=encoding, newline="") as fh:
                reader = csv.reader(fh)
                return [row for row in reader]
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode CSV file {file_path}")


def chunk_rows(rows: Sequence[list[Any]], size: int) -> Iterable[list[list[Any]]]:
    for idx in range(0, len(rows), size):
        yield [[str(cell) if cell is not None else "" for cell in row] for row in rows[idx : idx + size]]


def get_client(service_account_path: str) -> gspread.Client:
    resolved_path = resolve_service_account_path(service_account_path)
    return gspread.service_account(filename=resolved_path)


def open_sheet(env: dict[str, str]) -> tuple[gspread.Spreadsheet, gspread.Worksheet]:
    client = get_client(env["GOOGLE_SERVICE_ACCOUNT_JSON"])
    spreadsheet = client.open_by_key(env["GOOGLE_SPREADSHEET_ID"])
    worksheet_title = env["GOOGLE_WORKSHEET_TITLE"]
    try:
        worksheet = spreadsheet.worksheet(worksheet_title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_title, rows=2000, cols=26)
    return spreadsheet, worksheet


def replace_sheet_data(
    worksheet: gspread.Worksheet,
    data_rows: list[list[str]],
    batch_size: int,
    logger: logging.Logger,
) -> None:
    worksheet.clear()
    if not data_rows:
        return

    # gspread wants 2D lists. Respect API quotas by chunking large datasets.
    updates = list(chunk_rows(data_rows, batch_size))
    start_row = 1
    for chunk in updates:
        end_row = start_row + len(chunk) - 1
        end_col = len(max(chunk, key=len)) if chunk else 0
        range_label = f"A{start_row}"
        if end_col:
            from gspread.utils import rowcol_to_a1

            end_cell = rowcol_to_a1(start_row + len(chunk) - 1, end_col)
            range_label = f"A{start_row}:{end_cell}"

        worksheet.update(range_label, chunk, value_input_option="RAW")
        logger.info("Sheet chunk written starting at row %d for %d rows", start_row, len(chunk))
        start_row += len(chunk)


@dataclass(slots=True)
class ProcessedEmail:
    email_id: str
    csv_path: Path
    batch_id: str
    timestamp: datetime


async def fetch_csvs(env: dict[str, str], logger: logging.Logger) -> list[ProcessedEmail]:
    download_dir = Path(env["CSV_DOWNLOAD_DIR"])
    download_dir.mkdir(parents=True, exist_ok=True)

    service = EmailIntegrationService(
        imap_server=env["EMAIL_IMAP_SERVER"],
        imap_port=as_int(env["EMAIL_IMAP_PORT"], 993),
        email_address=env["EMAIL_ADDRESS"],
        email_password=env["EMAIL_PASSWORD"],
        download_dir=download_dir,
    )

    if not await service.connect():
        raise RuntimeError("Failed to connect to IMAP server")

    lookback_days = max(0, as_int(env["EMAIL_LOOKBACK_DAYS"], 10))
    since_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    try:
        csvs = await service.check_for_new_csvs(since_date=since_date)
        processed: list[ProcessedEmail] = []
        for csv_meta in csvs:
            batch_id = csv_meta["batch_id"]
            file_path = Path(csv_meta["file_path"])
            timestamp = csv_meta["timestamp"]
            email_id = csv_meta.get("email_id", "")
            processed.append(ProcessedEmail(email_id=email_id, csv_path=file_path, batch_id=batch_id, timestamp=timestamp))
            # prevent duplicate handling within single run
            service.monitor.mark_processed(batch_id)
        logger.info("Downloaded %d CSV attachment(s)", len(processed))
        return processed
    finally:
        service.disconnect()


def select_latest(processed_csvs: list[ProcessedEmail]) -> ProcessedEmail | None:
    if not processed_csvs:
        return None
    return max(processed_csvs, key=lambda item: item.timestamp)


async def main() -> None:
    env = get_env()
    logger = setup_logger()

    try:
        processed_csvs = await fetch_csvs(env, logger)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Email fetch failed: %s", exc)
        raise SystemExit(1) from exc

    if not processed_csvs:
        logger.info("No CSV found in inbox; nothing to ingest.")
        return

    latest = select_latest(processed_csvs)
    if latest is None:
        logger.info("No CSV selected after processing attachments.")
        return

    logger.info(
        "Processing latest CSV file=%s batch_id=%s timestamp=%s",
        latest.csv_path,
        latest.batch_id,
        latest.timestamp.isoformat(),
    )

    try:
        rows = read_csv(latest.csv_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to read CSV %s: %s", latest.csv_path, exc)
        raise SystemExit(1) from exc

    if not rows:
        logger.warning("CSV contains no rows: %s", latest.csv_path)
        return

    try:
        _, worksheet = open_sheet(env)
        batch_size = max(500, as_int(env["GOOGLE_BATCH_UPDATE_SIZE"], 5000))
        replace_sheet_data(worksheet, rows, batch_size=batch_size, logger=logger)
        logger.info("Sheet update complete for worksheet=%s rows=%d", worksheet.title, len(rows))
    except APIError as exc:
        logger.exception("Google Sheets API error: %s", exc)
        raise SystemExit(1) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to update sheet: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())

