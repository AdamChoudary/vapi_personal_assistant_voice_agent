import os
from pathlib import Path
from dotenv import load_dotenv
import httpx

if Path('.env').exists():
    load_dotenv('.env')
else:
    load_dotenv('env.example')

api_key = os.getenv('VAPI_API_KEY')
assistant_id = os.getenv('VAPI_ASSISTANT_ID')
base_url = os.getenv('VAPI_BASE_URL', 'https://api.vapi.ai')

with open('tool_check.log', 'w', encoding='utf-8') as log:
    log.write(f'API key present: {bool(api_key)}\n')
    log.write(f'Assistant ID present: {bool(assistant_id)}\n')

    if not api_key or not assistant_id:
        log.write('Missing credentials, aborting.\n')
        raise SystemExit('Missing VAPI credentials')

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{base_url}/assistant/{assistant_id}", headers=headers)
        resp.raise_for_status()
        data = resp.json()

    model_tools = data.get('model', {}).get('tools', [])
    current_tools = []
    for tool in model_tools:
        func = tool.get('function')
        name = None
        if isinstance(func, dict):
            name = func.get('name')
        if not name:
            name = tool.get('name')
        if name:
            current_tools.append(name)

    expected_tools = [
        'customer_search',
        'customer_details',
        'finance_info',
        'delivery_stops',
        'next_scheduled_delivery',
        'default_products',
        'orders_search',
        'account_balance',
        'invoice_history',
        'invoice_detail',
        'payment_methods',
        'products_catalog',
        'products',
        'customer_contracts',
        'route_stops',
        'send_contract',
        'contract_status',
        'declined_payment_call',
        'collections_call',
        'delivery_reminder_call'
    ]

    current_set = set(current_tools)
    expected_set = set(expected_tools)

    missing = sorted(expected_set - current_set)
    extra = sorted(current_set - expected_set)

    log.write(f'Current tools ({len(current_tools)}):\n')
    for name in sorted(current_tools):
        log.write(f' - {name}\n')

    log.write(f'\nMissing tools ({len(missing)}):\n')
    for name in missing:
        log.write(f' - {name}\n')

    log.write(f'\nUnexpected tools ({len(extra)}):\n')
    for name in extra:
        log.write(f' - {name}\n')
