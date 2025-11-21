"""
One-shot pipeline:
1. Ingest latest declined-payment CSV from email into Google Sheets.
2. Trigger outbound call processing from the updated sheet.

Intended to be run on Fly.io via cron (e.g., every minute).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Awaitable

from dotenv import load_dotenv

from scripts.ingest_email_csv_to_sheet import main as ingest_sheet  # noqa: F401
from scripts.run_outbound_from_sheet import main as trigger_outbound  # noqa: F401


logger = logging.getLogger("email_to_outbound_pipeline")


async def run_step(step: Callable[[], Awaitable[None]], name: str) -> None:
    try:
        logger.info("Starting %s", name)
        await step()
        logger.info("Completed %s", name)
    except SystemExit as exc:
        logger.error("%s exited via SystemExit status=%s", name, exc.code)
        # Swallow to allow outer poller to wait and retry
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("%s failed: %s", name, exc)
        raise RuntimeError(f"{name} failed") from exc


async def pipeline() -> None:
    await run_step(ingest_sheet, "Email ingestion")
    await run_step(trigger_outbound, "Outbound dispatcher")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    load_dotenv()
    asyncio.run(pipeline())


if __name__ == "__main__":
    main()

