"""
Long-running email polling worker.

Runs email_to_outbound_pipeline every N seconds (default: 60).
Designed to run on Fly.io with restart policy 'always'.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Awaitable, Callable

from dotenv import load_dotenv

from scripts.email_to_outbound_pipeline import pipeline

DEFAULT_INTERVAL = 60


def get_interval() -> int:
    raw = os.getenv("EMAIL_POLL_INTERVAL_SECONDS")
    if not raw:
        return DEFAULT_INTERVAL
    try:
        value = int(raw)
        return max(15, value)
    except ValueError:
        return DEFAULT_INTERVAL


async def run_forever(step: Callable[[], Awaitable[None]], interval: int) -> None:
    while True:
        try:
            await step()
        except Exception:  # noqa: BLE001
            logging.exception("Polling iteration failed")
        await asyncio.sleep(interval)


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    interval = get_interval()
    logging.info("Starting email poll worker interval=%ss", interval)
    asyncio.run(run_forever(pipeline, interval))


if __name__ == "__main__":
    main()

