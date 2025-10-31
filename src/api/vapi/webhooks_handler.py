"""
Vapi webhook handler for function/tool calls.

This handler receives function call requests from Vapi and routes them
to the appropriate internal tool endpoints. It provides:
- Function call routing
- Call context management
- Error handling and retry logic
- Response formatting for Vapi
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
import structlog

from src.core.deps import get_fontis_client
from src.services.fontis_client import FontisClient
from src.core.exceptions import FontisAPIError
from src.schemas.vapi import VapiFunctionCall, VapiWebhookEvent

# Import all tool handlers
from src.api.tools import customer, delivery, billing, contracts, routes, onboarding

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/vapi", tags=["vapi"])

# In-memory call context store (replace with Redis in production)
call_contexts: dict[str, dict[str, Any]] = {}


def store_call_context(call_id: str, key: str, value: Any) -> None:
    """Store context data for a call session."""
    if call_id not in call_contexts:
        call_contexts[call_id] = {}
    call_contexts[call_id][key] = value


def get_call_context(call_id: str, key: str, default: Any = None) -> Any:
    """Retrieve context data for a call session."""
    return call_contexts.get(call_id, {}).get(key, default)


def clear_call_context(call_id: str) -> None:
    """Clear context data after call ends."""
    if call_id in call_contexts:
        del call_contexts[call_id]


@router.post("/webhooks")
async def handle_vapi_webhook(
    event: VapiWebhookEvent,
    background_tasks: BackgroundTasks,
    fontis: FontisClient = Depends(get_fontis_client)
):
    """
    Handle incoming webhooks from Vapi.
    
    Vapi sends various webhook events:
    - function-call: AI wants to call a tool
    - call-start: New call initiated
    - call-end: Call completed
    - transcript: Real-time transcription
    - hang: Call disconnected
    """
    event_type = event.type
    
    logger.info(
        "vapi_webhook_received",
        event_type=event_type,
        call_id=event.call_id if hasattr(event, 'call_id') else None
    )
    
    # Route based on event type
    if event_type == "function-call":
        return await handle_function_call(event, fontis)
    
    elif event_type == "call-start":
        # Initialize call context
        if hasattr(event, 'call_id'):
            store_call_context(event.call_id, "started_at", event.timestamp)
            logger.info("call_started", call_id=event.call_id)
        return {"success": True, "message": "Call started"}
    
    elif event_type == "call-end":
        # Clean up call context
        if hasattr(event, 'call_id'):
            background_tasks.add_task(clear_call_context, event.call_id)
            logger.info("call_ended", call_id=event.call_id)
        return {"success": True, "message": "Call ended"}
    
    elif event_type in ["transcript", "speech-update"]:
        # Log transcript for debugging
        logger.debug(
            "transcript_received",
            call_id=event.call_id if hasattr(event, 'call_id') else None,
            transcript=event.transcript if hasattr(event, 'transcript') else None
        )
        return {"success": True}
    
    elif event_type == "hang":
        # Call disconnected
        if hasattr(event, 'call_id'):
            background_tasks.add_task(clear_call_context, event.call_id)
            logger.info("call_hung_up", call_id=event.call_id)
        return {"success": True, "message": "Call hung up"}
    
    else:
        # Unknown event type
        logger.warning("unknown_webhook_event", event_type=event_type)
        return {"success": True, "message": "Event received"}


async def handle_function_call(
    event: VapiWebhookEvent,
    fontis: FontisClient
) -> dict[str, Any]:
    """
    Handle function/tool call requests from Vapi.
    
    Routes the function call to the appropriate internal tool endpoint
    and returns a formatted response for Vapi to speak.
    """
    function_name = event.function_name
    parameters = event.parameters or {}
    call_id = event.call_id
    
    logger.info(
        "function_call_received",
        function_name=function_name,
        call_id=call_id,
        parameters=parameters
    )
    
    try:
        # Route to appropriate handler
        result = await route_function_call(
            function_name=function_name,
            parameters=parameters,
            call_id=call_id,
            fontis=fontis
        )
        
        # Store important context (customerId, deliveryId)
        if function_name in ["customer_search", "customer_details"]:
            if result.get("success") and result.get("data"):
                data = result["data"]
                if isinstance(data, dict):
                    # Store customer info for subsequent calls
                    if "customerId" in data:
                        store_call_context(call_id, "customerId", data["customerId"])
                    if "deliveryId" in data:
                        store_call_context(call_id, "deliveryId", data["deliveryId"])
                    if "name" in data:
                        store_call_context(call_id, "customerName", data["name"])
        
        logger.info(
            "function_call_success",
            function_name=function_name,
            call_id=call_id
        )
        
        # Return the result directly - VAPI expects the tool result, not wrapped
        return result
        
    except FontisAPIError as e:
        logger.error(
            "function_call_error",
            function_name=function_name,
            call_id=call_id,
            error=str(e)
        )
        # Return error in format VAPI expects
        return {
            "success": False,
            "message": "I'm having trouble accessing that information right now. Let me try again or connect you with someone who can help.",
            "error": str(e)
        }
    
    except Exception as e:
        logger.error(
            "function_call_unexpected_error",
            function_name=function_name,
            call_id=call_id,
            error=str(e),
            exc_info=True
        )
        # Return error in format VAPI expects
        return {
            "success": False,
            "message": "I encountered an unexpected issue. Let me connect you with a representative who can assist you.",
            "error": str(e)
        }


async def route_function_call(
    function_name: str,
    parameters: dict[str, Any],
    call_id: str,
    fontis: FontisClient
) -> dict[str, Any]:
    """
    Route function call to appropriate internal tool endpoint.
    
    This acts as a dispatcher, matching Vapi function names to your
    internal FastAPI tool endpoints.
    """
    
    # Customer tools
    if function_name == "customer_search":
        from src.schemas.tools import CustomerSearchTool
        params = CustomerSearchTool(**parameters)
        return await customer_search_handler(params, fontis)
    
    elif function_name == "customer_details":
        from src.schemas.tools import CustomerDetailsTool
        params = CustomerDetailsTool(**parameters)
        return await customer_details_handler(params, fontis)
    
    elif function_name == "finance_info":
        from src.schemas.tools import FinanceDeliveryInfoTool
        params = FinanceDeliveryInfoTool(**parameters)
        return await finance_info_handler(params, fontis)
    
    # Delivery tools
    elif function_name == "delivery_stops":
        from src.schemas.tools import DeliveryStopsTool
        params = DeliveryStopsTool(**parameters)
        return await delivery_stops_handler(params, fontis)
    
    elif function_name == "next_delivery":
        from src.schemas.tools import NextScheduledDeliveryTool
        params = NextScheduledDeliveryTool(**parameters)
        return await next_delivery_handler(params, fontis)
    
    elif function_name == "default_products":
        from src.schemas.tools import DefaultProductsTool
        params = DefaultProductsTool(**parameters)
        return await default_products_handler(params, fontis)
    
    elif function_name == "orders_search":
        from src.schemas.tools import OrdersSearchTool
        params = OrdersSearchTool(**parameters)
        return await orders_search_handler(params, fontis)
    
    # Billing tools
    elif function_name == "account_balance":
        from src.schemas.tools import AccountBalanceTool
        params = AccountBalanceTool(**parameters)
        return await account_balance_handler(params, fontis)
    
    elif function_name == "invoice_history":
        from src.schemas.tools import InvoiceHistoryTool
        params = InvoiceHistoryTool(**parameters)
        return await invoice_history_handler(params, fontis)
    
    elif function_name == "invoice_detail":
        from src.schemas.tools import InvoiceDetailTool
        params = InvoiceDetailTool(**parameters)
        return await invoice_detail_handler(params, fontis)
    
    elif function_name == "payment_methods":
        from src.schemas.tools import BillingMethodsTool
        params = BillingMethodsTool(**parameters)
        return await payment_methods_handler(params, fontis)
    
    elif function_name == "products_catalog" or function_name == "products":
        from src.schemas.tools import ProductsTool
        params = ProductsTool(**parameters)
        return await products_catalog_handler(params, fontis)
    
    # Contract tools
    elif function_name == "customer_contracts":
        from src.schemas.tools import ContractsTool
        params = ContractsTool(**parameters)
        return await customer_contracts_handler(params, fontis)
    
    # Route tools
    elif function_name == "route_stops":
        from src.schemas.tools import RouteStopsTool
        params = RouteStopsTool(**parameters)
        return await route_stops_handler(params, fontis)
    
    # Onboarding tools (JotForm)
    elif function_name == "send_contract":
        from src.schemas.tools import SendContractTool
        params = SendContractTool(**parameters)
        return await send_contract_handler(params)
    
    elif function_name == "contract_status":
        from src.schemas.tools import ContractStatusTool
        params = ContractStatusTool(**parameters)
        return await contract_status_handler(params)
    
    else:
        raise ValueError(f"Unknown function: {function_name}")


# Individual tool handlers (simplified wrappers around your existing tools)

async def customer_search_handler(params, fontis: FontisClient) -> dict:
    """Handle customer_search function call."""
    response = await fontis.search_customers(
        lookup=params.lookup,
        offset=params.offset,
        take=params.take
    )
    return response


async def customer_details_handler(params, fontis: FontisClient) -> dict:
    """Handle customer_details function call."""
    response = await fontis.get_customer_details(
        customer_id=params.customer_id,
        include_inactive=params.include_inactive
    )
    return response


async def finance_info_handler(params, fontis: FontisClient) -> dict:
    """Handle finance_info function call."""
    # If delivery_id not provided, get customer's primary delivery
    delivery_id = params.delivery_id
    if not delivery_id:
        # Get customer details to find their delivery IDs
        customer = await fontis.get_customer_details(
            customer_id=params.customer_id,
            include_inactive=False
        )
        if customer.get("success") and customer.get("data"):
            # Try to get first delivery ID from customer data
            deliveries = customer["data"].get("deliveries", [])
            if deliveries:
                delivery_id = deliveries[0].get("deliveryId")
    
    if not delivery_id:
        return {
            "success": False,
            "message": "Unable to find delivery information for this customer. They may not have any active deliveries set up.",
            "error": "No delivery ID available"
        }
    
    response = await fontis.get_customer_finance_info(
        customer_id=params.customer_id,
        delivery_id=delivery_id
    )
    return response


async def delivery_stops_handler(params, fontis: FontisClient) -> dict:
    """Handle delivery_stops function call."""
    response = await fontis.get_delivery_stops(
        customer_id=params.customer_id,
        offset=params.offset,
        take=params.take
    )
    return response


async def next_delivery_handler(params, fontis: FontisClient) -> dict:
    """Handle next_delivery function call."""
    response = await fontis.get_next_scheduled_delivery(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id,
        days_ahead=params.days_ahead
    )
    return response


async def default_products_handler(params, fontis: FontisClient) -> dict:
    """Handle default_products function call."""
    response = await fontis.get_default_products(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id
    )
    return response


async def orders_search_handler(params, fontis: FontisClient) -> dict:
    """Handle orders_search function call."""
    response = await fontis.search_orders(
        ticket_number=params.ticket_number,
        customer_id=params.customer_id,
        delivery_id=params.delivery_id,
        only_open_orders=params.only_open_orders,
        web_products_only=params.web_products_only
    )
    return response


async def account_balance_handler(params, fontis: FontisClient) -> dict:
    """Handle account_balance function call."""
    response = await fontis.get_account_balances(
        customer_id=params.customer_id,
        include_inactive=params.include_inactive
    )
    return response


async def invoice_history_handler(params, fontis: FontisClient) -> dict:
    """Handle invoice_history function call."""
    response = await fontis.get_invoice_history(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id,
        number_of_months=params.number_of_months,
        offset=params.offset,
        take=params.take,
        descending=params.descending
    )
    return response


async def invoice_detail_handler(params, fontis: FontisClient) -> dict:
    """Handle invoice_detail function call."""
    response = await fontis.get_invoice_detail(
        customer_id=params.customer_id,
        invoice_key=params.invoice_key,
        invoice_date=params.invoice_date,
        include_signature=params.include_signature,
        include_payments=params.include_payments
    )
    return response


async def payment_methods_handler(params, fontis: FontisClient) -> dict:
    """Handle payment_methods function call."""
    response = await fontis.get_billing_methods(
        customer_id=params.customer_id,
        include_inactive=params.include_inactive
    )
    return response


async def products_catalog_handler(params, fontis: FontisClient) -> dict:
    """Handle products_catalog function call."""
    response = await fontis.get_products(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id,
        postal_code=params.postal_code,
        internet_only=params.internet_only,
        categories=params.categories,
        default_products=params.default_products,
        offset=params.offset,
        take=params.take
    )
    return response


async def customer_contracts_handler(params, fontis: FontisClient) -> dict:
    """Handle customer_contracts function call."""
    response = await fontis.get_customer_contracts(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id
    )
    return response


async def route_stops_handler(params, fontis: FontisClient) -> dict:
    """Handle route_stops function call."""
    response = await fontis.get_route_stops(
        route=params.route,
        route_date=params.route_date,
        account_number=params.account_number
    )
    return response


async def send_contract_handler(params) -> dict:
    """Handle send_contract function call (JotForm integration)."""
    # Import JotForm client
    from src.services.jotform_client import JotFormClient
    from src.config import settings
    
    jotform = JotFormClient(
        api_key=settings.jotform_api_key,
        form_id=settings.jotform_form_id
    )
    
    response = await jotform.send_contract_email(
        customer_email=params.customer_email,
        customer_name=params.customer_name,
        service_address=params.service_address
    )
    return response


async def contract_status_handler(params) -> dict:
    """Handle contract_status function call (JotForm integration)."""
    from src.services.jotform_client import JotFormClient
    from src.config import settings
    
    jotform = JotFormClient(
        api_key=settings.jotform_api_key,
        form_id=settings.jotform_form_id
    )
    
    response = await jotform.get_submission_status(
        submission_id=params.submission_id
    )
    return response

