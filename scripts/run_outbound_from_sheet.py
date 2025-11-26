"""
Read rows from Google Sheets and trigger outbound calls at scale.

Environment variables:
    GOOGLE_SERVICE_ACCOUNT_JSON (required)
    GOOGLE_SPREADSHEET_ID       (required)
    GOOGLE_WORKSHEET_TITLE      (default: 2025)
    OUTBOUND_DEFAULT_COUNTRY_CODE (default: +92)
    OUTBOUND_MAX_CONCURRENT_CALLS (default: 5)
    OUTBOUND_BATCH_WRITE_SIZE     (default: 50)
    OUTBOUND_LOG_LEVEL            (default: INFO)
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import islice
from typing import Any, Iterable

import gspread
from dotenv import load_dotenv
from gspread.utils import rowcol_to_a1

from src.services.outbound_call_service import OutboundCallService
from scripts.service_account_loader import resolve_service_account_path

REQUIRED_ENV = [
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GOOGLE_SPREADSHEET_ID",
]
OPTIONAL_ENV = {
    "GOOGLE_WORKSHEET_TITLE": "2025",
    "OUTBOUND_DEFAULT_COUNTRY_CODE": "+92",
    "OUTBOUND_MAX_CONCURRENT_CALLS": "5",
    "OUTBOUND_BATCH_WRITE_SIZE": "50",
    "OUTBOUND_LOG_LEVEL": "INFO",
}

DATA_HEADERS = {
    "customer_id": "customer_id",
    "first_name": "billing_first_name",
    "last_name": "billing_last_name",
    "phone": "billing_phone",
    "amount": "amount",
    "delivery_date": "delivery_date",
}

TRACKING_HEADERS = {
    "status": "outbound_status",
    "call_id": "outbound_call_id",
    "last_attempt": "outbound_last_attempt_utc",
    "error": "outbound_error",
}

ALLOWED_STATUSES = {"", "pending", "retry", "failed", "no_answer"}
CALL_TYPE_MAP = {
    "declined_payment": "declined_payment",
    "declined_payment_call": "declined_payment",
    "declined": "declined_payment",
    "collections": "collections",
    "collection": "collections",
    "collections_call": "collections",
    "collections_follow_up": "collections",
    "delivery_reminder": "delivery_reminder",
    "delivery": "delivery_reminder",
    "delivery_call": "delivery_reminder",
    "delivery_follow_up": "delivery_reminder",
}
MAX_ERROR_MESSAGE_LENGTH = 500
CALL_TYPE_KEYWORDS = {
    "declined": "declined_payment",
    "failed": "declined_payment",
    "card": "declined_payment",
    "collection": "collections",
    "past due": "collections",
    "overdue": "collections",
    "delivery": "delivery_reminder",
    "reminder": "delivery_reminder",
}

load_dotenv()


def load_env() -> dict[str, str]:
    missing = [var for var in REQUIRED_ENV if not os.getenv(var)]
    if missing:
        raise SystemExit(f"Missing env vars: {', '.join(missing)}")

    env = {var: os.getenv(var) for var in REQUIRED_ENV}  # type: ignore[dict-item]
    for key, default in OPTIONAL_ENV.items():
        env[key] = os.getenv(key, default)
    return env  # type: ignore[return-value]


def configure_logging(level: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    return logging.getLogger("outbound_sheet_worker")


def ensure_headers(worksheet: gspread.Worksheet) -> dict[str, int]:
    header_row = worksheet.row_values(1)
    header_row = [header.strip() for header in header_row]
    missing = [header for header in TRACKING_HEADERS.values() if header not in header_row]

    if missing:
        worksheet.add_cols(len(missing))
        header_row.extend(missing)
        end_col = rowcol_to_a1(1, len(header_row))  # type: ignore[arg-type]
        worksheet.batch_update([{"range": f"A1:{end_col}", "values": [header_row]}])

    required_data_headers = [DATA_HEADERS["customer_id"], DATA_HEADERS["phone"]]
    missing_required = [header for header in required_data_headers if header not in header_row]
    if missing_required:
        raise SystemExit(
            f"Worksheet is missing required headers: {', '.join(missing_required)}. "
            "Run scripts/setup_google_sheet_from_csv.py to initialize the sheet."
        )

    return {header: idx + 1 for idx, header in enumerate(header_row)}


def chunked(iterable: Iterable[Any], size: int) -> Iterable[list[Any]]:
    iterator = iter(iterable)
    while chunk := list(islice(iterator, size)):
        yield chunk


def resolve_value(row: dict[str, Any], *candidates: str) -> str | None:
    for key in candidates:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return None


def normalize_phone(raw: str | None, default_code: str) -> str | None:
    if not raw:
        return None
    stripped = raw.strip().replace(" ", "")
    if stripped.startswith("+"):
        return stripped

    default_digits = default_code.lstrip("+")
    stripped = stripped.lstrip("+")

    if stripped.startswith(default_digits):
        return f"+{stripped}"
    return f"{default_code}{stripped}".replace("++", "+")


def normalize_amount(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = str(raw).strip().replace("$", "").replace(",", "")
    return cleaned or None


def to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def determine_call_type(row: dict[str, Any]) -> str:
    primary = row.get("type")
    candidates = [
        primary,
        row.get("transaction_source"),
        row.get("description"),
        row.get("custom_fields"),
    ]

    for value in candidates:
        if not value:
            continue
        cleaned = str(value).strip().lower()
        normalized = cleaned.replace(" ", "_")
        if normalized in CALL_TYPE_MAP:
            return CALL_TYPE_MAP[normalized]
        for keyword, mapped in CALL_TYPE_KEYWORDS.items():
            if keyword in cleaned:
                return mapped

    return "declined_payment"


def format_currency(value: str | float | None) -> str | None:
    if value is None or value == "":
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        try:
            num = float(str(value).replace("$", "").replace(",", ""))
        except (TypeError, ValueError):
            return str(value)
    return f"${num:,.2f}"


def build_call_reason(call_type: str, customer_name: str | None, amount: str | None, delivery_date: str | None) -> str:
    """Build a clear summary of why we're calling - for agent context only."""
    if call_type == "declined_payment":
        if amount:
            return f"Payment of {amount} was declined. Current account balance may be higher."
        return "Payment was declined. Please check account balance."
    if call_type == "collections":
        if amount:
            return f"Account has past due balance of {amount}. Payment needed to avoid service interruption."
        return "Account has past due balance. Payment needed to avoid service interruption."
    if call_type == "delivery_reminder":
        if delivery_date:
            return f"Delivery scheduled for {delivery_date}. Remind customer to have empty bottles ready."
        return "Upcoming delivery scheduled. Remind customer to have empty bottles ready."
    return f"Outbound call for {call_type.replace('_', ' ')}."


def build_sms_reason(call_type: str, amount: str | None, delivery_date: str | None) -> str:
    if call_type == "declined_payment":
        if amount:
            return f"your recent payment of {amount} did not go through"
        return "we noticed an issue with your recent payment"
    if call_type == "collections":
        if amount:
            return f"your account has a past-due balance of {amount}"
        return "your account has a past-due balance"
    if call_type == "delivery_reminder":
        if delivery_date:
            return f"you have a delivery scheduled on {delivery_date}"
        return "you have an upcoming delivery"
    return "we have an important update regarding your Fontis Water account"


def build_first_message(call_type: str, customer_name: str | None, amount: str | None, delivery_date: str | None) -> str:
    """Build a natural, professional first message with customer name."""
    if not customer_name:
        customer_name = "there"
    
    # Natural greeting with customer name - this will be spoken by Vapi
    if call_type == "declined_payment":
        return f"Hi {customer_name}! This is Riley calling from Fontis Water. How are you doing today?"
    elif call_type == "collections":
        return f"Hi {customer_name}! This is Riley calling from Fontis Water. I hope I'm catching you at a good time?"
    elif call_type == "delivery_reminder":
        return f"Hi {customer_name}! This is Riley calling from Fontis Water. How are you doing today?"
    else:
        return f"Hi {customer_name}! This is Riley calling from Fontis Water. How are you doing today?"


def build_custom_message(call_type: str, customer_name: str | None, amount: str | None, delivery_date: str | None) -> str:
    """Build a simple message that ONLY mentions SMS will be received."""
    return "You'll receive a text message on your phone with all the details."


def build_assistant_overrides(
    customer_data: dict[str, Any],
    amount_pretty: str | None,
    delivery_date: str | None,
    row_index: int,
    env: dict[str, str],
) -> dict[str, Any]:
    call_type = customer_data.get("call_type", "declined_payment")
    customer_name = customer_data.get("name")

    first_message = build_first_message(call_type, customer_name, amount_pretty, delivery_date)
    call_reason = build_call_reason(call_type, customer_name, amount_pretty, delivery_date)
    custom_message = build_custom_message(call_type, customer_name, amount_pretty, delivery_date)

    metadata_overrides: dict[str, str] = {
        "call_reason_summary": call_reason,
        "custom_message_context": custom_message,  # CRITICAL: This is the actual message with real data
        "outbound_source": "google_sheet_pipeline",
        "call_type_label": call_type.replace("_", " "),
        "sheet_row_index": str(row_index),
        "customer_name": customer_name or "",
        "customer_phone": customer_data.get("phone_number", ""),
        "spreadsheet_id": env["GOOGLE_SPREADSHEET_ID"],
        "worksheet_title": env["GOOGLE_WORKSHEET_TITLE"],
    }

    if amount_pretty:
        metadata_overrides["call_amount_display"] = amount_pretty
        # CRITICAL: Use the amount_formatted_str from customer_data (already correctly formatted)
        # This ensures we use the exact amount read from the correct column
        if call_type == "declined_payment":
            # Use the declined_amount from customer_data (already formatted to 2 decimals)
            declined_amount = customer_data.get("declined_amount")
            if declined_amount:
                metadata_overrides["declined_amount"] = declined_amount
            else:
                # Fallback: extract from amount_pretty
                amount_clean = amount_pretty.replace("$", "").replace(",", "").strip()
                try:
                    amount_float = float(amount_clean)
                    metadata_overrides["declined_amount"] = f"{amount_float:.2f}"
                except (ValueError, TypeError):
                    metadata_overrides["declined_amount"] = amount_clean
        elif call_type == "collections":
            # Use the past_due_amount from customer_data (already formatted to 2 decimals)
            past_due_amount = customer_data.get("past_due_amount")
            if past_due_amount:
                metadata_overrides["past_due_amount"] = past_due_amount
            else:
                # Fallback: extract from amount_pretty
                amount_clean = amount_pretty.replace("$", "").replace(",", "").strip()
                try:
                    amount_float = float(amount_clean)
                    metadata_overrides["past_due_amount"] = f"{amount_float:.2f}"
                except (ValueError, TypeError):
                    metadata_overrides["past_due_amount"] = amount_clean
    if delivery_date:
        metadata_overrides["call_delivery_date"] = delivery_date
        metadata_overrides["delivery_date"] = delivery_date

    metadata_overrides["sms_reason"] = build_sms_reason(call_type, amount_pretty, delivery_date)

    return {
        "metadata": metadata_overrides,
        "assistantOverrides": {
            "firstMessage": first_message,
        },
    }


@dataclass(slots=True)
class RowOutcome:
    row_index: int
    status: str
    call_id: str | None
    last_attempt_iso: str
    error: str | None = None


async def handle_row(
    row_index: int,
    row: dict[str, Any],
    env: dict[str, str],
    outbound: OutboundCallService,
    logger: logging.Logger,
) -> RowOutcome | None:
    status_raw = str(row.get(TRACKING_HEADERS["status"], "") or "").strip().lower()
    if status_raw not in ALLOWED_STATUSES:
        return None

    phone = normalize_phone(
        resolve_value(row, DATA_HEADERS["phone"], "shipping_phone"),
        env["OUTBOUND_DEFAULT_COUNTRY_CODE"],
    )
    customer_id = resolve_value(row, DATA_HEADERS["customer_id"], "id")
    first_name = resolve_value(row, DATA_HEADERS["first_name"], "shipping_first_name")
    last_name = resolve_value(row, DATA_HEADERS["last_name"], "shipping_last_name")
    # CRITICAL: Determine call type FIRST to know which amount column to read
    call_type = determine_call_type(row)
    
    # Read amount from appropriate column based on call type
    # For declined_payment: read the declined amount (not account balance)
    # For collections: read the past due amount (not account balance)
    if call_type == "declined_payment":
        # Try declined_amount column first, then fall back to amount
        amount_raw = normalize_amount(resolve_value(row, "declined_amount", DATA_HEADERS["amount"], "base_amount", "amount_authorized"))
    elif call_type == "collections":
        # Try past_due_amount column first, then fall back to amount
        amount_raw = normalize_amount(resolve_value(row, "past_due_amount", "past_due", DATA_HEADERS["amount"], "base_amount", "amount_authorized"))
    else:
        # For delivery reminders, amount might not be relevant
        amount_raw = normalize_amount(resolve_value(row, DATA_HEADERS["amount"], "base_amount", "amount_authorized"))
    
    amount_value = to_float(amount_raw)
    delivery_date = resolve_value(row, DATA_HEADERS["delivery_date"], "next_delivery_date")

    if not phone or not customer_id:
        logger.warning("Row %d skipped: missing phone or customer_id", row_index)
        return RowOutcome(
            row_index=row_index,
            status="Skipped: missing phone/customer_id",
            call_id=None,
            last_attempt_iso=datetime.now(timezone.utc).isoformat(),
            error="",
        )

    customer_name = " ".join(filter(None, [first_name, last_name])) or "Valued Customer"
    
    # Format amount properly - ensure it's a float with 2 decimals
    if amount_value is not None:
        amount_formatted = float(amount_value)
        amount_formatted_str = f"{amount_formatted:.2f}"
    elif amount_raw:
        try:
            amount_formatted = float(amount_raw)
            amount_formatted_str = f"{amount_formatted:.2f}"
        except (ValueError, TypeError):
            amount_formatted = None
            amount_formatted_str = None
    else:
        amount_formatted = None
        amount_formatted_str = None
    
    # Set the correct amount field based on call type
    customer_data = {
        "customer_id": customer_id,
        "name": customer_name,
        "amount_raw": amount_raw,
        "delivery_date": delivery_date,
        "phone_number": phone,
        "call_type": call_type,
        "description": row.get("description"),
        "transaction_status": row.get("status"),
        "type": row.get("type"),
        "sheet_row_index": row_index,
    }
    
    # Set the correct amount field based on call type
    # CRITICAL: Only set the amount field that matches the call type
    # Do NOT set account_balance to the same value - this causes confusion
    if amount_formatted_str:
        if call_type == "declined_payment":
            customer_data["declined_amount"] = amount_formatted_str
            # Do NOT set account_balance - it might be different and would confuse the assistant
        elif call_type == "collections":
            customer_data["past_due_amount"] = amount_formatted_str
            # Do NOT set account_balance - it might be different and would confuse the assistant

    # Format amount for display (with $ and commas) - use the formatted float
    if amount_formatted is not None:
        amount_pretty = format_currency(amount_formatted)
    else:
        amount_pretty = None
    assistant_overrides = build_assistant_overrides(
        customer_data=customer_data,
        amount_pretty=amount_pretty,
        delivery_date=delivery_date,
        row_index=row_index,
        env=env,
    )

    # Log which columns were found for debugging
    amount_source = "unknown"
    if call_type == "declined_payment":
        if row.get("declined_amount"):
            amount_source = "declined_amount column"
        elif row.get(DATA_HEADERS["amount"]):
            amount_source = f"{DATA_HEADERS['amount']} column"
        elif row.get("base_amount"):
            amount_source = "base_amount column"
    elif call_type == "collections":
        if row.get("past_due_amount"):
            amount_source = "past_due_amount column"
        elif row.get("past_due"):
            amount_source = "past_due column"
        elif row.get(DATA_HEADERS["amount"]):
            amount_source = f"{DATA_HEADERS['amount']} column"
    
    logger.info(
        "Row %d: initiating %s call -> customer_id=%s phone=%s amount=%s (formatted=%s, source=%s)",
        row_index,
        call_type,
        customer_id,
        phone,
        amount_raw or "N/A",
        amount_pretty or "N/A",
        amount_source,
    )
    logger.info(
        "Row %d: outbound call context metadata=%s first_message=%s",
        row_index,
        assistant_overrides.get("metadata", {}),
        assistant_overrides.get("assistantOverrides", {}).get("firstMessage"),
    )

    try:
                call_result = await outbound.initiate_call(
                    customer_phone=phone,
            call_type=call_type,
                    customer_data=customer_data,
            assistant_overrides=assistant_overrides,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Row %d: call failed for customer_id=%s", row_index, customer_id)
        return RowOutcome(
            row_index=row_index,
            status="failed",
            call_id=None,
            last_attempt_iso=datetime.now(timezone.utc).isoformat(),
            error=str(exc)[:MAX_ERROR_MESSAGE_LENGTH],
        )

    call_id = str(call_result.get("id") or "")
    logger.info("Row %d: call scheduled id=%s status=%s", row_index, call_id, call_result.get("status"))

    return RowOutcome(
        row_index=row_index,
        status="Dialing",
        call_id=call_id,
        last_attempt_iso=datetime.now(timezone.utc).isoformat(),
        error="",
    )


def build_updates(
    outcomes: list[RowOutcome],
    header_map: dict[str, int],
) -> list[dict[str, list[list[str]]]]:
    updates: list[dict[str, list[list[str]]]] = []

    for outcome in outcomes:
        status_cell = rowcol_to_a1(outcome.row_index, header_map[TRACKING_HEADERS["status"]])
        updates.append({"range": status_cell, "values": [[outcome.status]]})

        call_id_cell = rowcol_to_a1(outcome.row_index, header_map[TRACKING_HEADERS["call_id"]])
        updates.append({"range": call_id_cell, "values": [[outcome.call_id or ""]]})

        last_attempt_cell = rowcol_to_a1(outcome.row_index, header_map[TRACKING_HEADERS["last_attempt"]])
        updates.append({"range": last_attempt_cell, "values": [[outcome.last_attempt_iso]]})

        error_cell = rowcol_to_a1(outcome.row_index, header_map[TRACKING_HEADERS["error"]])
        updates.append({"range": error_cell, "values": [[outcome.error or ""]]})

    return updates


async def process_rows(
    sheet: gspread.Worksheet,
    env: dict[str, str],
    logger: logging.Logger,
) -> None:
    header_map = ensure_headers(sheet)
    rows = sheet.get_all_records(default_blank="")
    total_rows = len(rows)
    logger.info("Loaded %d rows from worksheet '%s'", total_rows, sheet.title)

    outbound = OutboundCallService()

    max_concurrency = max(1, int(env["OUTBOUND_MAX_CONCURRENT_CALLS"]))
    semaphore = asyncio.Semaphore(max_concurrency)

    async def guard_handle(row_index: int, row_data: dict[str, Any]) -> RowOutcome | None:
        async with semaphore:
            return await handle_row(row_index, row_data, env, outbound, logger)

    tasks = [
        asyncio.create_task(guard_handle(idx, row))
        for idx, row in enumerate(rows, start=2)
    ]

    outcomes: list[RowOutcome] = []
    processed = 0

    for task in asyncio.as_completed(tasks):
        result = await task
        processed += 1
        if result:
            outcomes.append(result)

        if processed % 100 == 0:
            logger.info("Processed %d/%d rows", processed, total_rows)

    logger.info("Completed processing %d rows (%d outcomes to persist)", processed, len(outcomes))

    if not outcomes:
        return

    batch_size = max(1, int(env["OUTBOUND_BATCH_WRITE_SIZE"]))
    updates = build_updates(outcomes, header_map)

    for chunk in chunked(updates, batch_size):
        sheet.batch_update(chunk)
        logger.debug("Applied batch update with %d cells", len(chunk))


async def main() -> None:
    env = load_env()
    logger = configure_logging(env["OUTBOUND_LOG_LEVEL"])
    sheet = get_sheet(env)
    await process_rows(sheet, env, logger)


def get_sheet(env: dict[str, str]) -> gspread.Worksheet:
    resolved = resolve_service_account_path(env["GOOGLE_SERVICE_ACCOUNT_JSON"])
    gc = gspread.service_account(filename=resolved)
    spreadsheet = gc.open_by_key(env["GOOGLE_SPREADSHEET_ID"])
    return spreadsheet.worksheet(env["GOOGLE_WORKSHEET_TITLE"])


if __name__ == "__main__":
    asyncio.run(main())