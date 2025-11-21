"""Update the Vapi outbound assistant prompt from docs/outbound system prompt.txt."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID_OUTBOUND") or os.getenv("VAPI_ASSISTANT_ID")
VAPI_BASE_URL = os.getenv("VAPI_BASE_URL", "https://api.vapi.ai")

if not VAPI_API_KEY or not ASSISTANT_ID:
    raise SystemExit("Missing VAPI_API_KEY or VAPI_ASSISTANT_ID in environment.")

# Read the outbound system prompt
prompt_file = Path("docs/outbound system prompt.txt")
if not prompt_file.exists():
    raise SystemExit(f"Outbound prompt file not found: {prompt_file}")

system_prompt = prompt_file.read_text(encoding="utf-8")

headers = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}

with httpx.Client(timeout=30.0) as client:
    assistant = client.get(
        f"{VAPI_BASE_URL}/assistant/{ASSISTANT_ID}", headers=headers
    ).json()

model = assistant.get("model", {})
payload = {
    "model": {
        "model": model.get("model", "gpt-4-turbo"),
        "provider": model.get("provider", "openai"),
        "messages": [{"role": "system", "content": system_prompt}],
        "tools": model.get("tools", []),
    },
    "firstMessage": assistant.get(
        "firstMessage",
        "Hello! I'm Riley from Fontis Water. How can I help you today?",
    ),
    "name": assistant.get("name", "Riley"),
    "voice": assistant.get("voice"),
}

with httpx.Client(timeout=30.0) as client:
    resp = client.patch(
        f"{VAPI_BASE_URL}/assistant/{ASSISTANT_ID}",
        headers=headers,
        json=payload,
    )
    resp.raise_for_status()

print(f"Updated outbound assistant prompt (ID: {ASSISTANT_ID}).")

