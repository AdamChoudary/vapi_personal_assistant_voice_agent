import os
import re
from pathlib import Path
import httpx
from dotenv import load_dotenv

if Path('.env').exists():
    load_dotenv('.env')
else:
    load_dotenv('env.example')

api_key = os.getenv('VAPI_API_KEY')
assistant_id = os.getenv('VAPI_ASSISTANT_ID')
base_url = os.getenv('VAPI_BASE_URL', 'https://api.vapi.ai')

if not api_key or not assistant_id:
    raise SystemExit('Missing VAPI credentials')

text = Path('scripts/setup_new_assistant_complete.py').read_text(encoding='utf-8')
match = re.search(r'SYSTEM_PROMPT = """(.*?)"""', text, re.S)
if not match:
    raise SystemExit('SYSTEM_PROMPT not found')
system_prompt = match.group(1)

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

with httpx.Client(timeout=30.0) as client:
    response = client.get(f"{base_url}/assistant/{assistant_id}", headers=headers)
    response.raise_for_status()
    assistant = response.json()
    model = assistant.get('model', {})
    payload = {
        'model': {
            'model': model.get('model', 'gpt-4-turbo'),
            'provider': model.get('provider', 'openai'),
            'messages': [
                {'role': 'system', 'content': system_prompt}
            ],
            'tools': model.get('tools', [])
        },
        'firstMessage': assistant.get('firstMessage', "Hello! I'm Riley from Fontis Water. How can I help you today?"),
        'name': assistant.get('name', 'Riley'),
        'voice': assistant.get('voice')
    }
    patch_resp = client.patch(
        f"{base_url}/assistant/{assistant_id}",
        headers=headers,
        json=payload
    )
    patch_resp.raise_for_status()
    print('System prompt updated successfully.')
