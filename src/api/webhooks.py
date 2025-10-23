from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from src.core.deps import verify_vapi_webhook
from src.schemas.vapi import VapiWebhookRequest

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/vapi", dependencies=[Depends(verify_vapi_webhook)])
async def vapi_webhook(payload: VapiWebhookRequest) -> dict[str, Any]:
    """
    Receive webhook events from Vapi during calls.
    
    This endpoint handles real-time events like:
    - Call started
    - Call ended
    - Speech events
    - Tool call requests
    """
    # Log the webhook event
    print(f"📞 Vapi webhook received: {payload.message.role}")
    
    # Handle different event types
    # TODO: Implement event-specific logic
    
    return {
        "status": "received",
        "message": "Webhook processed successfully"
    }


@router.post("/vapi/function-call")
async def vapi_function_call(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Handle Vapi function/tool calls.
    
    Vapi will call this endpoint when the AI needs to execute a tool.
    """
    function_name = payload.get("function", {}).get("name")
    arguments = payload.get("function", {}).get("arguments", {})
    
    print(f"🔧 Tool call: {function_name} with args: {arguments}")
    
    # Route to appropriate tool handler
    # TODO: Implement tool routing logic
    
    return {
        "result": f"Tool {function_name} executed",
        "data": {}
    }

