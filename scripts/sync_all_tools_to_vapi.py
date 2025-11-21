"""
Automated Vapi Tool Sync Script

This script automatically syncs all 17 backend endpoints to Vapi assistant as tools.
Solves the hallucination problem by ensuring assistant has access to all functions.
"""

import asyncio
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
VAPI_BASE_URL = "https://api.vapi.ai"

# Get tunnel URL from command line or detect
TUNNEL_URL = sys.argv[1] if len(sys.argv) > 1 else None


# Complete tool definitions matching backend endpoints
TOOL_DEFINITIONS = [
    # CUSTOMER TOOLS
    {
        "name": "customer_search",
        "description": "Search for a customer by name, phone, address, or account number. Returns customer ID, contact info, and account status. Use this as the FIRST step when customer provides ANY identifier.",
        "parameters": {
            "type": "object",
            "properties": {
                "lookup": {
                    "type": "string",
                    "description": "Search term - can be name, phone, address, or account number (e.g. '005895', 'John Smith', '123 Main St')"
                }
            },
            "required": ["lookup"]
        }
    },
    {
        "name": "customer_details",
        "description": "Get detailed customer information using internal customerId. Only use this with customerId obtained from customer_search.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Internal customer ID from customer_search result"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "finance_info",
        "description": "Get customer financial summary and delivery IDs. Returns deliveryId needed for other delivery/billing tools.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID from search"
                }
            },
            "required": ["customer_id"]
        }
    },
    
    # BILLING TOOLS
    {
        "name": "account_balance",
        "description": "Get customer's current account balance, total due, and open invoices summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID from search"
                },
                "include_inactive": {
                    "type": "boolean",
                    "description": "Include inactive delivery stops (default: false)"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "invoice_history",
        "description": "Get detailed invoice and payment history for a customer. Shows all transactions, payments, and invoice details.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID from search"
                },
                "delivery_id": {
                    "type": "string",
                    "description": "Delivery ID from finance_info"
                },
                "days_back": {
                    "type": "number",
                    "description": "Number of days to look back (default: 180)"
                }
            },
            "required": ["customer_id", "delivery_id"]
        }
    },
    {
        "name": "invoice_detail",
        "description": "Get detailed breakdown of a specific invoice including line items and charges.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                },
                "invoice_key": {
                    "type": "string",
                    "description": "Invoice key from invoice_history"
                },
                "invoice_date": {
                    "type": "string",
                    "description": "Invoice date from invoice_history"
                }
            },
            "required": ["customer_id", "invoice_key", "invoice_date"]
        }
    },
    {
        "name": "payment_methods",
        "description": "Get payment methods on file for customer (credit cards, ACH). Shows masked card numbers and types.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "payment_expiry_alerts",
        "description": "Identify payment methods that are expired or expiring soon so customers can update them.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                },
                "days_threshold": {
                    "type": "integer",
                    "description": "Days before expiry to flag cards (default 60)"
                },
                "include_inactive": {
                    "type": "boolean",
                    "description": "Include inactive payment methods"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "products",
        "description": "Get product catalog with prices. Use for new customers or when they ask about available products.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    
    # DELIVERY TOOLS
    {
        "name": "delivery_stops",
        "description": "Get all delivery locations for a customer. Most customers have 1, some have multiple.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "next_scheduled_delivery",
        "description": "Get customer's next scheduled delivery date, time window, and products to be delivered.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                },
                "delivery_id": {
                    "type": "string",
                    "description": "Delivery ID from finance_info"
                },
                "days_ahead": {
                    "type": "number",
                    "description": "Days to look ahead (default: 45)"
                }
            },
            "required": ["customer_id", "delivery_id"]
        }
    },
    {
        "name": "default_products",
        "description": "Get customer's standing order - the products they regularly receive on each delivery.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                },
                "delivery_id": {
                    "type": "string",
                    "description": "Delivery ID"
                }
            },
            "required": ["customer_id", "delivery_id"]
        }
    },
    {
        "name": "search_orders",
        "description": "Search for specific delivery orders by date range or status.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                },
                "delivery_id": {
                    "type": "string",
                    "description": "Delivery ID"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD)"
                }
            },
            "required": ["customer_id", "delivery_id"]
        }
    },
    
    # OTHER TOOLS
    {
        "name": "get_contracts",
        "description": "Get customer's service agreements and contracts. Shows contract type, duration, and renewal status.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "customer_contracts",
        "description": "Alias for get_contracts to retrieve customer service agreements.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "route_stops",
        "description": "Get all stops on a specific route for a date. Used to verify if delivery was completed or skipped.",
        "parameters": {
            "type": "object",
            "properties": {
                "route_date": {
                    "type": "string",
                    "description": "Route date (YYYY-MM-DD)"
                },
                "route": {
                    "type": "string",
                    "description": "Route code"
                },
                "account_number": {
                    "type": "string",
                    "description": "Optional: filter to specific customer"
                }
            },
            "required": ["route_date", "route"]
        }
    },
    {
        "name": "delivery_summary",
        "description": "Summarize delivery route, driver, equipment, and next delivery context for a customer stop.",
        "parameters": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "includeNextDelivery": {"type": "boolean", "description": "Include next scheduled delivery lookup"},
                "includeDefaults": {"type": "boolean", "description": "Include standing order/default product summary"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "delivery_schedule",
        "description": "Retrieve scheduled deliveries for a customer within a date range, including completion status.",
        "parameters": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "fromDate": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "toDate": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "historyDays": {"type": "integer", "description": "Days in the past when fromDate omitted"},
                "futureDays": {"type": "integer", "description": "Days in the future when toDate omitted"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "work_order_status",
        "description": "Check recent off-route deliveries or service work orders for a customer.",
        "parameters": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "limit": {"type": "integer", "description": "Number of recent orders to review"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "pricing_breakdown",
        "description": "Provide pricing breakdown for the customer's standing order and optional catalog excerpt.",
        "parameters": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "postalCode": {"type": "string", "description": "Postal code for pricing lookup"},
                "internetOnly": {"type": "boolean", "description": "Restrict catalog to internet/web products"},
                "includeCatalogExcerpt": {"type": "boolean", "description": "Include a short catalog excerpt"}
            },
            "required": ["customerId", "postalCode"]
        }
    },
    {
        "name": "order_change_status",
        "description": "Confirm if a pending order or delivery change request exists for the customer.",
        "parameters": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "ticketNumber": {"type": "string", "description": "Specific ticket number to confirm"},
                "onlyOpenOrders": {"type": "boolean", "description": "Limit lookup to open/pending orders"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "send_contract",
        "description": "Send onboarding contract to new customer via JotForm. Use for new customer signups.",
        "parameters": {
            "type": "object",
            "properties": {
                "customerName": {"type": "string", "description": "Full legal name"},
                "email": {"type": "string", "description": "Primary email address"},
                "phone": {"type": "string", "description": "Phone number (recommend E.164)"},
                "address": {"type": "string", "description": "Service street address"},
                "city": {"type": "string", "description": "Service city"},
                "state": {"type": "string", "description": "Two-letter state code"},
                "postalCode": {"type": "string", "description": "ZIP or postal code"},
                "deliveryPreference": {"type": "string", "description": "Preferred delivery day"},
                "companyName": {"type": "string", "description": "Business or organization name"},
                "productsOfInterest": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Products the customer is interested in"
                },
                "specialInstructions": {
                    "type": "string",
                    "description": "Any onboarding notes or delivery instructions"
                },
                "marketingOptIn": {
                    "type": "boolean",
                    "description": "Did the customer opt into marketing communications?"
                },
                "sendEmail": {
                    "type": "boolean",
                    "description": "Send the contract via JotForm email invitation (default true)"
                }
            },
            "required": [
                "customerName",
                "email",
                "phone",
                "address",
                "city",
                "state",
                "postalCode"
            ]
        }
    },
    {
        "name": "contract_status",
        "description": "Check the status of a submitted onboarding contract.",
        "parameters": {
            "type": "object",
            "properties": {
                "submission_id": {
                    "type": "string",
                    "description": "JotForm submission ID"
                }
            },
            "required": ["submission_id"]
        }
    },

    # OUTBOUND CALL TOOLS
    {
        "name": "declined_payment_call",
        "description": "Initiate a declined payment outreach call to notify the customer about a failed payment and request updated information.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Fontis customer ID"
                },
                "customer_phone": {
                    "type": "string",
                    "description": "Customer phone number in E.164 format"
                },
                "customer_name": {
                    "type": "string",
                    "description": "Customer name"
                },
                "declined_amount": {
                    "type": "number",
                    "description": "Amount that was declined"
                },
                "account_balance": {
                    "type": "number",
                    "description": "Current account balance"
                }
                },
            "required": ["customer_id", "customer_phone", "customer_name"]
        }
    },
    {
        "name": "collections_call",
        "description": "Initiate a collections call for a past-due account to discuss outstanding balances and next steps.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Fontis customer ID"
                },
                "customer_phone": {
                    "type": "string",
                    "description": "Customer phone number in E.164 format"
                },
                "customer_name": {
                    "type": "string",
                    "description": "Customer name"
                },
                "past_due_amount": {
                    "type": "number",
                    "description": "Past due amount"
                },
                "days_past_due": {
                    "type": "integer",
                    "description": "Days the account is past due"
                }
            },
            "required": ["customer_id", "customer_phone", "customer_name", "past_due_amount"]
        }
    },
    {
        "name": "delivery_reminder_call",
        "description": "Send a delivery reminder by phone or SMS, optionally warning about account holds before scheduled service.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Fontis customer ID"
                },
                "customer_phone": {
                    "type": "string",
                    "description": "Customer phone number in E.164 format"
                },
                "customer_name": {
                    "type": "string",
                    "description": "Customer name"
                },
                "delivery_date": {
                    "type": "string",
                    "description": "Scheduled delivery date (YYYY-MM-DD)"
                },
                "send_sms": {
                    "type": "boolean",
                    "description": "Send an SMS instead of placing a call"
                },
                "account_on_hold": {
                    "type": "boolean",
                    "description": "Account is on hold or past due"
                }
            },
            "required": ["customer_id", "customer_phone", "customer_name", "delivery_date"]
        }
    }
]

# Mapping from tool names to backend endpoints
ENDPOINT_MAP = {
    # JSON endpoint returns {"result": "..."} for VAPI consumption
    "customer_search": "/tools/customer/search-vapi",
    "customer_details": "/tools/customer/details",
    "finance_info": "/tools/customer/finance-info",
    "account_balance": "/tools/billing/balance",
    "invoice_history": "/tools/billing/invoice-history",
    "invoice_detail": "/tools/billing/invoice-detail",
    "payment_methods": "/tools/billing/payment-methods",
    "payment_expiry_alerts": "/tools/billing/payment-expiry-alerts",
    "products": "/tools/billing/products",
    "delivery_stops": "/tools/delivery/stops",
    "next_scheduled_delivery": "/tools/delivery/next-scheduled",
    "default_products": "/tools/delivery/default-products",
    "search_orders": "/tools/delivery/search-orders",
    "get_contracts": "/tools/contracts/get-contracts",
    "route_stops": "/tools/routes/stops",
    "delivery_summary": "/tools/delivery/summary",
    "delivery_schedule": "/tools/delivery/schedule",
    "work_order_status": "/tools/delivery/work-orders",
    "pricing_breakdown": "/tools/delivery/pricing-breakdown",
    "order_change_status": "/tools/delivery/order-change-status",
    "send_contract": "/tools/onboarding/send-contract",
    "customer_contracts": "/tools/contracts/get-contracts",
    "orders_search": "/tools/delivery/search-orders",
    "products_catalog": "/tools/billing/products",
    "contract_status": "/tools/onboarding/contract-status",
    "declined_payment_call": "/admin/outbound/declined-payment",
    "collections_call": "/admin/outbound/collections",
    "delivery_reminder_call": "/admin/outbound/delivery-reminder"
}


async def detect_cloudflared_url() -> str | None:
    """Detect cloudflared tunnel URL."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get("http://127.0.0.1:20241/metrics")
            if response.status_code == 200:
                import re
                match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', response.text)
                if match:
                    return match.group(0)
    except Exception:
        pass
    return None


async def get_current_assistant() -> dict[str, Any]:
    """Fetch current assistant configuration."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{VAPI_BASE_URL}/assistant/{VAPI_ASSISTANT_ID}",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


async def sync_tools(tunnel_url: str) -> dict[str, Any]:
    """Sync all 17 tools to Vapi assistant."""
    
    print("[INFO] Fetching current assistant configuration...")
    current = await get_current_assistant()
    
    print(f"[OK] Current assistant: {current.get('name', 'Unknown')}")
    print(f"  Current tools: {len(current.get('model', {}).get('tools', []))}")
    
    # Remove read-only fields
    readonly_fields = ["id", "orgId", "createdAt", "updatedAt", "isServerUrlSecretSet"]
    for field in readonly_fields:
        current.pop(field, None)
    
    # Clear deprecated functions array
    if "functions" in current:
        current["functions"] = []
    
    # Build new tools array
    print(f"\n[INFO] Building {len(TOOL_DEFINITIONS)} tools...")
    new_tools = []
    
    for tool_def in TOOL_DEFINITIONS:
        tool_name = tool_def["name"]
        endpoint = ENDPOINT_MAP.get(tool_name, f"/tools/{tool_name}")
        
        # VAPI needs the FULL URL including the endpoint path
        full_url = f"{tunnel_url}{endpoint}"
        
        vapi_tool = {
            "type": "function",
            "server": {
                "url": full_url,  # Full URL with endpoint path
                "secret": INTERNAL_API_KEY
            },
            "function": {
                "name": tool_name,
                "description": tool_def["description"],
                "parameters": tool_def["parameters"]
            }
        }

        # Reduce validation errors by declaring a permissive returns schema for key tools
        if tool_name == "customer_search":
            # Encourage strict param extraction
            vapi_tool["function"]["strict"] = True
        
        new_tools.append(vapi_tool)
        print(f"  - {tool_name} -> {full_url}")
    
    # Update model.tools
    if "model" not in current:
        current["model"] = {}
    
    current["model"]["tools"] = new_tools
    
    # Update assistant via API
    print(f"\n[INFO] Updating Vapi assistant configuration...")
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{VAPI_BASE_URL}/assistant/{VAPI_ASSISTANT_ID}",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=current,
            timeout=60.0
        )
        response.raise_for_status()
        result = response.json()
    
    print(f"\n[OK] Successfully synced {len(new_tools)} tools!")
    return result


async def main():
    """Main execution."""
    print("=== Vapi Tool Sync Script ===\n")
    print("This will sync ALL 17 backend endpoints to Vapi assistant")
    print("=" * 60)
    
    # Validate environment
    if not VAPI_API_KEY:
        print("ERROR: VAPI_API_KEY not set")
        sys.exit(1)
    
    if not VAPI_ASSISTANT_ID:
        print("ERROR: VAPI_ASSISTANT_ID not set")
        sys.exit(1)
    
    if not INTERNAL_API_KEY:
        print("ERROR: INTERNAL_API_KEY not set (needed for tool authentication)")
        sys.exit(1)
    
    # Get tunnel URL
    tunnel_url = TUNNEL_URL
    
    if not tunnel_url:
        print("\n[INFO] No URL provided, detecting cloudflared tunnel...")
        tunnel_url = await detect_cloudflared_url()
        
        if not tunnel_url:
            print("\nERROR: Could not detect tunnel URL")
            print("Usage: python scripts/sync_all_tools_to_vapi.py <tunnel_url>")
            print("Example: python scripts/sync_all_tools_to_vapi.py https://xyz.trycloudflare.com")
            sys.exit(1)
    
    print(f"\n[INFO] Using tunnel URL: {tunnel_url}\n")
    
    try:
        result = await sync_tools(tunnel_url)
        
        print("\n" + "=" * 60)
        print("SYNC COMPLETE")
        print("=" * 60)
        print(f"\n[OK] All {len(TOOL_DEFINITIONS)} tools are now configured")
        print(f"[OK] Server URL: {tunnel_url}")
        print(f"[OK] Authentication: Configured with INTERNAL_API_KEY")
        
        print("\nTools synced:")
        for i, tool_def in enumerate(TOOL_DEFINITIONS, 1):
            print(f"  {i}. {tool_def['name']}")
        
        print("\nNext steps:")
        print("  1. Test a call: +16783034022")
        print("  2. Try: 'What's my balance?' or 'Show my invoices'")
        print("  3. Watch dashboard for tool calls")
        print("  4. Assistant should now have access to all synced tools.")
        
    except httpx.HTTPError as e:
        print(f"\nERROR syncing tools: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Unexpected failure: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

