# Create or update a Google Sheet worksheet using the header row from a CSV template.
#
# Environment variables required:
#   GOOGLE_SERVICE_ACCOUNT_JSON  - path to service account JSON
#   GOOGLE_SPREADSHEET_NAME      - spreadsheet name to create/open
#   GOOGLE_WORKSHEET_TITLE       - sheet/tab name to create or clear
#   CSV_TEMPLATE_PATH            - CSV file whose header row will be copied

from __future__ import annotations

import csv
import os
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

REQUIRED_ENV_VARS = [
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GOOGLE_SPREADSHEET_NAME",
    "GOOGLE_WORKSHEET_TITLE",
    "CSV_TEMPLATE_PATH",
]

OPTIONAL_ENV_VARS = [
    "GOOGLE_SPREADSHEET_ID",
]


def load_env_vars() -> dict[str, str | None]:
    """Load required environment variables or exit with a helpful error."""
    load_dotenv()
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

    env: dict[str, str | None] = {var: os.getenv(var) for var in REQUIRED_ENV_VARS}
    env.update({var: os.getenv(var) for var in OPTIONAL_ENV_VARS})
    return env


def read_csv(csv_path: str) -> list[list[str]]:
    """Read all rows of the CSV (header + data) with encoding fallbacks."""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV template not found: {csv_file}")

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            with csv_file.open("r", encoding=encoding, newline="") as fh:
                reader = csv.reader(fh)
                rows = [row for row in reader]
            break
        except UnicodeDecodeError as err:
            last_error = err
            continue
    else:
        raise last_error or UnicodeDecodeError("utf-8", b"", 0, 1, "Unable to decode CSV")

    if not rows:
        raise ValueError(f"CSV file is empty: {csv_file}")

    return [[cell.strip() for cell in row] for row in rows]


def get_client(sa_path: str) -> gspread.Client:
    """Authorize a gspread client using the provided service account file."""
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    credentials = Credentials.from_service_account_file(sa_path, scopes=scopes)
    return gspread.authorize(credentials)


def ensure_sheet(
    client: gspread.Client,
    spreadsheet_name: str,
    spreadsheet_id: str | None = None,
) -> gspread.Spreadsheet:
    """Open the spreadsheet if it exists; otherwise create it."""
    if spreadsheet_id:
        try:
            return client.open_by_key(spreadsheet_id)
        except gspread.SpreadsheetNotFound as exc:
            raise SystemExit(
                "Spreadsheet ID provided but not found. "
                "Ensure the service account has at least viewer access."
            ) from exc
    try:
        return client.open(spreadsheet_name)
    except gspread.SpreadsheetNotFound:
        try:
            return client.create(spreadsheet_name)
        except gspread.exceptions.APIError as exc:  # type: ignore[attr-defined]
            raise SystemExit(
                "Unable to create spreadsheet. If you created it manually in your "
                "personal Drive, share it with the service account and set "
                "GOOGLE_SPREADSHEET_ID in .env."
            ) from exc


def ensure_worksheet(
    spreadsheet: gspread.Spreadsheet,
    worksheet_title: str,
    data_rows: list[list[str]],
) -> gspread.Worksheet:
    """Create or clear the worksheet and populate it with data."""
    try:
        worksheet = spreadsheet.worksheet(worksheet_title)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_title,
            rows=str(max(len(data_rows), 1000)),
            cols=str(len(data_rows[0])),
        )

    worksheet.update("A1", data_rows)
    return worksheet


def main() -> None:
    env = load_env_vars()

    data_rows = read_csv(env["CSV_TEMPLATE_PATH"])
    headers = data_rows[0]
    client = get_client(env["GOOGLE_SERVICE_ACCOUNT_JSON"])
    spreadsheet = ensure_sheet(
        client,
        env["GOOGLE_SPREADSHEET_NAME"],
        spreadsheet_id=env.get("GOOGLE_SPREADSHEET_ID"),
    )
    worksheet = ensure_worksheet(spreadsheet, env["GOOGLE_WORKSHEET_TITLE"], data_rows)

    print("✅ Google Sheet initialized")
    print(f"Spreadsheet: {spreadsheet.url}")
    print(f"Worksheet:   {worksheet.title}")
    print(f"Headers:     {headers}")


if __name__ == "__main__":
    main()
