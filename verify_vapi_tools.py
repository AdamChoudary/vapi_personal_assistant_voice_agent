import os
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Load env vars (prefer .env, fall back to env.example)
if Path('.env').exists():
    load_dotenv('.env')
else:
    load_dotenv('env.example')

api_key = os.getenv('VAPI_API_KEY')
assistant_id = os.getenv('VAPI_ASSISTANT_ID')
base_url = os.getenv('VAPI_BASE_URL', 'https://api.vapi.ai')

if not api_key or not assistant_id:
    raise SystemExit('Missing VAPI credentials or assistant ID')

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

with httpx.Client(timeout=30.0) as client:
    response = client.get(f"{base_url}/assistant/{assistant_id}", headers=headers)
    response.raise_for_status()
    payload = response.json()

model_tools = payload.get('model', {}).get('tools', [])

records = []
for tool in model_tools:
    function_block = tool.get('function')
    name = None
    url = tool.get('server', {}).get('url') if isinstance(tool.get('server'), dict) else None

    if isinstance(function_block, dict):
        name = function_block.get('name')
    if not name:
        name = tool.get('name')

    if name:
        records.append((name, url))

records.sort(key=lambda x: x[0])

print(f"Assistant name: {payload.get('name')}")
print(f"Tool count   : {len(records)}\n")
for idx, (name, url) in enumerate(records, start=1):
    print(f"{idx:2}. {name:<25} -> {url}")
