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
        "name": "customer_search",
        "description": "Search for customers by name, account number, phone, or address. ALWAYS use this first when customer provides any identifier.",
        "url": f"{BACKEND_URL}/tools/customer/search-vapi",
        "parameters": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term: customer name, account number, phone, or address"
                },
                "offset": {"type": "number", "default": 0},
                "take": {"type": "number", "default": 25}
            }
        }
    },
    {
        "name": "customer_details",
        "description": "Get detailed customer information using internal customerId from customer_search results.",
        "url": f"{BACKEND_URL}/tools/customer/details",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Internal customer ID from customer_search"}
            }
        }
    },
    {
        "name": "finance_info",
        "description": "Get customer financial summary (balance, last payment) and delivery information.",
        "url": f"{BACKEND_URL}/tools/customer/finance-info",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"},
                "deliveryId": {"type": "string", "description": "Optional delivery ID (auto-fetched if not provided)"}
            }
        }
    },
    {
        "name": "delivery_stops",
        "description": "Get all delivery locations for a customer.",
        "url": f"{BACKEND_URL}/tools/delivery/stops",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"}
            }
        }
    },
    {
        "name": "next_scheduled_delivery",
        "description": "Get customer's next scheduled delivery date, time window, and products.",
        "url": f"{BACKEND_URL}/tools/delivery/next-scheduled",
        "parameters": {
            "type": "object",
            "required": ["customerId", "deliveryId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"},
                "deliveryId": {"type": "string", "description": "Delivery ID from finance_info or delivery_stops"},
                "daysAhead": {"type": "number", "default": 45, "description": "Days ahead to search (max 90)"}
            }
        }
    },
    {
        "name": "default_products",
        "description": "Get customer's standing order - products they regularly receive.",
        "url": f"{BACKEND_URL}/tools/delivery/default-products",
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
        "name": "search_orders",
        "description": "Search for delivery orders by customer.",
        "url": f"{BACKEND_URL}/tools/delivery/orders/search",
        "parameters": {
            "type": "object",
            "required": ["customerId", "deliveryId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID"},
                "deliveryId": {"type": "string", "description": "Delivery ID"},
                "ticketNumber": {"type": "string", "description": "Optional ticket number"}
            }
        }
    },
    {
        "name": "account_balance",
        "description": "Get customer's current account balance, total due, and past due amounts.",
        "url": f"{BACKEND_URL}/tools/billing/balance",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"}
            }
        }
    },
    {
        "name": "invoice_history",
        "description": "Get detailed invoice and payment history for a customer.",
        "url": f"{BACKEND_URL}/tools/billing/invoice-history",
        "parameters": {
            "type": "object",
            "required": ["customerId", "deliveryId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"},
                "deliveryId": {"type": "string", "description": "Delivery ID from delivery_stops"},
                "numberOfMonths": {"type": "number", "default": 12, "description": "Months of history (max 24)"}
            }
        }
    },
    {
        "name": "invoice_detail",
        "description": "Get detailed line items for a specific invoice.",
        "url": f"{BACKEND_URL}/tools/billing/invoice-detail",
        "parameters": {
            "type": "object",
            "required": ["customerId", "invoiceKey", "invoiceDate"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID"},
                "invoiceKey": {"type": "string", "description": "Invoice key from invoice_history"},
                "invoiceDate": {"type": "string", "description": "Invoice date (YYYY-MM-DD)"}
            }
        }
    },
    {
        "name": "payment_methods",
        "description": "Get payment methods on file for customer (credit cards, ACH).",
        "url": f"{BACKEND_URL}/tools/billing/payment-methods",
        "parameters": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"}
            }
        }
    },
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
        "name": "send_contract",
        "description": "Send onboarding contract to new customer via JotForm. Use for new customer signups only.",
        "url": f"{BACKEND_URL}/tools/onboarding/send-contract",
        "parameters": {
            "type": "object",
            "required": ["customerName", "email", "phone", "address", "city", "state", "postalCode"],
            "properties": {
                "customerName": {"type": "string", "description": "Full customer name"},
                "email": {"type": "string", "description": "Customer email address"},
                "phone": {"type": "string", "description": "Customer phone number"},
                "address": {"type": "string", "description": "Street address"},
                "city": {"type": "string", "description": "City name"},
                "state": {"type": "string", "description": "State code (2 letters)"},
                "postalCode": {"type": "string", "description": "ZIP/postal code"}
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
        print("❌ Missing VAPI_API_KEY or INTERNAL_API_KEY")
        return 1
    
    print("=" * 80)
    print("🔧 CREATING STANDALONE VAPI TOOLS FOR DASHBOARD")
    print("=" * 80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Tools: {len(STANDALONE_TOOLS)}")
    print()
    
    async with httpx.AsyncClient() as client:
        print("1️⃣ Fetching existing tools...")
        existing_tools = await get_existing_tools(client)
        print(f"   Found {len(existing_tools)} existing tools")
        print()
        
        print("2️⃣ Creating/updating tools...")
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
                print(f"   ✓ {message}")
            else:
                failed += 1
                print(f"   ✗ {message}")
        
        print()
        print("=" * 80)
        print("✅ TOOL CREATION COMPLETE")
        print("=" * 80)
        print(f"   Created: {created}")
        print(f"   Updated: {updated}")
        print(f"   Failed: {failed}")
        print()
        print("📋 Next Steps:")
        print("   1. Go to VAPI Dashboard → Tools section")
        print("   2. Refresh the page (Ctrl+F5 or Cmd+Shift+R)")
        print("   3. You should see all tools listed")
        print("   4. Tools can be added to assistants from the Tools section")
        print()
        print("🔗 Dashboard: https://dashboard.vapi.ai/tools")
        print()
        
        return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
