"""
Create standalone VAPI tools that appear in the Tools dashboard section.
These tools are separate from assistant-specific tools and can be reused.
"""
import asyncio
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
VAPI_BASE_URL = "https://api.vapi.ai"
BACKEND_URL = "https://fontis-voice-agent.fly.dev"

# Tool definitions matching our setup_new_assistant_complete.py
STANDALONE_TOOLS = [

       
    {
        "name": "products",
        "description": "Get product catalog with prices. Use when customer asks about available products or pricing.",
        "url": f"{BACKEND_URL}/tools/billing/products",
        "parameters": {
            "type": "object",
            "required": [],
            "properties": {
                "customerId": {"type": "string", "description": "Optional customer ID for pricing"},
                "postalCode": {"type": "string", "description": "Optional postal code for pricing"}
            }
        }
    },
    {
        "name": "get_contracts",
        "description": "Get customer's service agreements and contracts.",
        "url": f"{BACKEND_URL}/tools/contracts/get-contracts",
        "parameters": {
            "type": "object",
            "required": ["customerId", "deliveryId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"},
                "deliveryId": {"type": "string", "description": "Delivery ID from delivery_stops"}
            }
        }
    },
    {
        "name": "route_stops",
        "description": "Get all stops on a specific route for a date. Used to verify if delivery was completed.",
        "url": f"{BACKEND_URL}/tools/routes/stops",
        "parameters": {
            "type": "object",
            "required": ["route", "routeDate"],
            "properties": {
                "route": {"type": "string", "description": "Route code (e.g., '19')"},
                "routeDate": {"type": "string", "description": "Route date in YYYY-MM-DD format"},
                "accountNumber": {"type": "string", "description": "Optional: filter to specific account"}
            }
        }
    },
    {
        "name": "payment_expiry_alerts",
        "description": "Identify payment methods that are expired or expiring soon so customers can update them.",
        "url": f"{BACKEND_URL}/tools/billing/payment-expiry-alerts",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID"},
                "daysThreshold": {"type": "integer", "description": "Days before expiry to trigger alert"},
                "includeInactive": {"type": "boolean", "description": "Include inactive payment methods"}
            }
        }
    },
    {
        "name": "delivery_summary",
        "description": "Summarize delivery route, driver assignment, equipment, and next delivery details for a customer.",
        "url": f"{BACKEND_URL}/tools/delivery/summary",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "includeNextDelivery": {"type": "boolean", "description": "Include next scheduled delivery lookup"},
                "includeDefaults": {"type": "boolean", "description": "Include standing order/default product summary"}
            }
        }
    },
    {
        "name": "delivery_schedule",
        "description": "Retrieve future and recent scheduled deliveries including completion or skip status.",
        "url": f"{BACKEND_URL}/tools/delivery/schedule",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "fromDate": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "toDate": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "historyDays": {"type": "integer", "description": "Days in the past when fromDate omitted"},
                "futureDays": {"type": "integer", "description": "Days in the future when toDate omitted"}
            }
        }
    },
    {
        "name": "work_order_status",
        "description": "Check recent off-route deliveries or service work orders for a customer stop.",
        "url": f"{BACKEND_URL}/tools/delivery/work-orders",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "limit": {"type": "integer", "description": "Number of recent orders to return"}
            }
        }
    },
    {
        "name": "pricing_breakdown",
        "description": "Provide standing order pricing totals and optional catalog excerpt for the customer.",
        "url": f"{BACKEND_URL}/tools/delivery/pricing-breakdown",
        "parameters": {
            "type": "object",
            "required": ["customerId", "postalCode"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "postalCode": {"type": "string", "description": "Postal code for pricing lookup"},
                "internetOnly": {"type": "boolean", "description": "Restrict catalog to internet/web products"},
                "includeCatalogExcerpt": {"type": "boolean", "description": "Include sample catalog pricing"}
            }
        }
    },
    {
        "name": "order_change_status",
        "description": "Confirm whether a pending order change or special delivery ticket exists for the customer.",
        "url": f"{BACKEND_URL}/tools/delivery/order-change-status",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "ticketNumber": {"type": "string", "description": "Specific ticket number to confirm"},
                "onlyOpenOrders": {"type": "boolean", "description": "Only list open/pending orders"}
            }
        }
    },
    {
        "name": "send_contract",
        "description": "Send onboarding contract to new customer via JotForm. Use for new customer signups only.",
        "url": f"{BACKEND_URL}/tools/onboarding/send-contract",
        "parameters": {
            "type": "object",
            "properties": {
                "customerName": {"type": "string", "description": "Full customer name"},
                "email": {"type": "string", "description": "Customer email address"},
                "phone": {"type": "string", "description": "Customer phone number"},
                "address": {"type": "string", "description": "Street address"},
                "city": {"type": "string", "description": "City name"},
                "state": {"type": "string", "description": "State code (2 letters)"},
                "postalCode": {"type": "string", "description": "ZIP/postal code"},
                "deliveryPreference": {"type": "string", "description": "Preferred delivery day"},
                "companyName": {"type": "string", "description": "Company or organization name"},
                "productsOfInterest": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Customer-selected products"
                },
                "specialInstructions": {"type": "string", "description": "Special instructions or notes"},
                "marketingOptIn": {"type": "boolean", "description": "Customer opted into marketing updates"},
                "sendEmail": {"type": "boolean", "description": "Send contract email via JotForm (default true)"}
            },
            "required": ["customerName", "email", "phone", "address", "city", "state", "postalCode"]
        }
    },

    # OUTBOUND CALL TOOLS
    {
        "name": "declined_payment_call",
        "description": "Initiate a declined payment outreach call to notify the customer about a failed payment and request updated information.",
        "url": f"{BACKEND_URL}/admin/outbound/declined-payment",
        "parameters": {
            "type": "object",
            "required": ["customerId", "customerPhone", "customerName"],
            "properties": {
                "customerId": {"type": "string", "description": "Fontis customer ID"},
                "customerPhone": {"type": "string", "description": "Customer phone number in E.164 format"},
                "customerName": {"type": "string", "description": "Customer name"},
                "declinedAmount": {"type": "number", "description": "Amount that was declined"},
                "accountBalance": {"type": "number", "description": "Current account balance"}
            }
        }
    },
    {
        "name": "collections_call",
        "description": "Initiate a collections call for a past-due account to discuss outstanding balances and next steps.",
        "url": f"{BACKEND_URL}/admin/outbound/collections",
        "parameters": {
            "type": "object",
            "required": ["customerId", "customerPhone", "customerName", "pastDueAmount"],
            "properties": {
                "customerId": {"type": "string", "description": "Fontis customer ID"},
                "customerPhone": {"type": "string", "description": "Customer phone number in E.164 format"},
                "customerName": {"type": "string", "description": "Customer name"},
                "pastDueAmount": {"type": "number", "description": "Past due amount"},
                "daysPastDue": {"type": "integer", "description": "Days the account is past due"}
            }
        }
    },
    {
        "name": "delivery_reminder_call",
        "description": "Send a delivery reminder by phone or SMS, optionally warning about account holds before scheduled service.",
        "url": f"{BACKEND_URL}/admin/outbound/delivery-reminder",
        "parameters": {
            "type": "object",
            "required": ["customerId", "customerPhone", "customerName", "deliveryDate"],
            "properties": {
                "customerId": {"type": "string", "description": "Fontis customer ID"},
                "customerPhone": {"type": "string", "description": "Customer phone number in E.164 format"},
                "customerName": {"type": "string", "description": "Customer name"},
                "deliveryDate": {"type": "string", "description": "Scheduled delivery date (YYYY-MM-DD)"},
                "sendSms": {"type": "boolean", "description": "Send an SMS instead of placing a call"},
                "accountOnHold": {"type": "boolean", "description": "Account is on hold or past due"}
            }
        }
    }
]


async def get_existing_tools(client: httpx.AsyncClient) -> dict[str, str]:
    """Fetch existing tools and create name->id mapping."""
    try:
        response = await client.get(
            f"{VAPI_BASE_URL}/tool",
            headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
            timeout=30.0
        )
        response.raise_for_status()
        tools = response.json()
        # Support both function and apiRequest tool types
        tool_map = {}
        for tool in tools:
            tool_name = tool.get("name") or tool.get("function", {}).get("name")
            if tool_name:
                tool_map[tool_name] = tool.get("id")
        return tool_map
    except httpx.HTTPStatusError:
        return {}


async def create_or_update_tool(client: httpx.AsyncClient, tool_def: dict[str, Any], existing_tools: dict[str, str]) -> tuple[bool, str]:
    """Create or update a standalone API Request tool."""
    # API Request tools use schema-based headers format
    tool_payload = {
        "type": "apiRequest",
        "name": tool_def["name"],
        "url": tool_def["url"],
        "method": "POST",
        "headers": {
            "type": "object",
            "properties": {
                "Content-Type": {
                    "type": "string",
                    "value": "application/json"
                },
                "Authorization": {
                    "type": "string",
                    "value": f"Bearer {INTERNAL_API_KEY}"
                }
            }
        },
        "body": tool_def["parameters"],
        "function": {
            "name": tool_def["name"],
            "description": tool_def["description"]
        },
        "variableExtractionPlan": {
            "schema": {
                "type": "object",
                "required": ["result"],
                "properties": {
                    "result": {
                        "type": "string"
                    }
                }
            },
            "aliases": []
        }
    }
    
    tool_name = tool_def["name"]
    
    # Check if tool exists and what type it is
    if tool_name in existing_tools:
        tool_id = existing_tools[tool_name]
        # Get existing tool to check type
        try:
            get_response = await client.get(
                f"{VAPI_BASE_URL}/tool/{tool_id}",
                headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
                timeout=30.0
            )
            get_response.raise_for_status()
            existing_tool = get_response.json()
            
            # If it's a function type tool, delete it first (can't change type via PATCH)
            if existing_tool.get("type") == "function":
                try:
                    await client.delete(
                        f"{VAPI_BASE_URL}/tool/{tool_id}",
                        headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
                        timeout=30.0
                    )
                    # Fall through to create new tool
                except httpx.HTTPStatusError:
                    pass  # Continue to try update/create
            elif existing_tool.get("type") == "apiRequest":
                # Can update apiRequest tools
                # Remove type field for updates (VAPI doesn't allow changing type)
                update_payload = {k: v for k, v in tool_payload.items() if k != "type"}
                try:
                    response = await client.patch(
                        f"{VAPI_BASE_URL}/tool/{tool_id}",
                        headers={
                            "Authorization": f"Bearer {VAPI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json=update_payload,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    return True, f"Updated: {tool_name}"
                except httpx.HTTPStatusError as e:
                    error = e.response.text[:200] if e.response else str(e)
                    return False, f"Failed to update {tool_name}: {error}"
        except httpx.HTTPStatusError:
            pass  # Tool might not exist, fall through to create
    
    # Create new tool (or recreate after delete)
    # Create new tool
    try:
        response = await client.post(
            f"{VAPI_BASE_URL}/tool",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=tool_payload,
            timeout=30.0
        )
        response.raise_for_status()
        return True, f"Created: {tool_name}"
    except httpx.HTTPStatusError as e:
        error = e.response.text[:200] if e.response else str(e)
        return False, f"Failed to create {tool_name}: {error}"


async def main() -> int:
    """Main execution."""
    if not VAPI_API_KEY or not INTERNAL_API_KEY:
        print("ERROR: Missing VAPI_API_KEY or INTERNAL_API_KEY")
        return 1
    
    print("=" * 80)
    print("=== CREATING STANDALONE VAPI TOOLS FOR DASHBOARD ===")
    print("=" * 80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Tools: {len(STANDALONE_TOOLS)}")
    print()
    
    async with httpx.AsyncClient() as client:
        print("STEP 1: Fetching existing tools...")
        existing_tools = await get_existing_tools(client)
        print(f"   Found {len(existing_tools)} existing tools")
        print()
        
        print("STEP 2: Creating/updating tools...")
        created = 0
        updated = 0
        failed = 0
        
        for tool_def in STANDALONE_TOOLS:
            success, message = await create_or_update_tool(client, tool_def, existing_tools)
            if success:
                if "Created" in message:
                    created += 1
                else:
                    updated += 1
                print(f"   OK {message}")
            else:
                failed += 1
                print(f"   ERROR {message}")
        
        print()
        print("=" * 80)
        print("TOOL CREATION COMPLETE")
        print("=" * 80)
        print(f"   Created: {created}")
        print(f"   Updated: {updated}")
        print(f"   Failed: {failed}")
        print()
        print("Next Steps:")
        print("   1. Go to VAPI Dashboard -> Tools section")
        print("   2. Refresh the page (Ctrl+F5 or Cmd+Shift+R)")
        print("   3. You should see all tools listed")
        print("   4. Tools can be added to assistants from the Tools section")
        print()
        print("Dashboard: https://dashboard.vapi.ai/tools")
        print()
        
        return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
