"""
Pydantic schemas for Vapi AI platform integration.

This module defines models for:
- Webhook payloads received from Vapi during calls
- Tool call requests from Vapi
- Responses sent back to Vapi

Design decisions:
- Flexible schemas (dict[str, Any]) for evolving Vapi API
- Type-safe where possible for validation
- Default factories for optional nested objects
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VapiMessage(BaseModel):
    """
    Message structure from Vapi webhooks.
    
    Represents a message in the conversation flow.
    """
    role: str  # "assistant", "user", "system", etc.
    content: str  # Message text


class VapiToolCall(BaseModel):
    """
    Tool call request from Vapi.
    
    Sent when Vapi AI decides to execute a function/tool.
    """
    id: str  # Unique tool call ID
    type: str = "function"  # Always "function" for tool calls
    function: dict[str, Any]  # Function name and arguments


class VapiWebhookRequest(BaseModel):
    """
    Webhook payload from Vapi during calls.
    
    Vapi sends webhooks for:
    - Call started/ended events
    - Speech recognition events
    - Tool execution requests
    - Error notifications
    
    Fields:
        message: Current message in conversation
        call: Call metadata (ID, status, duration, etc.)
        metadata: Custom metadata passed when creating call
    """
    message: VapiMessage
    call: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(extra="allow")  # Allow additional fields from Vapi


class VapiToolResponse(BaseModel):
    """
    Response format for Vapi tool calls.
    
    Sent back to Vapi after executing a tool/function.
    Vapi uses this data to continue the conversation.
    """
    results: list[dict[str, Any]]
    
    model_config = ConfigDict(extra="allow")


class VapiFunctionCall(BaseModel):
    """
    Function call request from Vapi.
    
    Sent when Vapi AI wants to execute a custom function/tool.
    """
    function_name: str = Field(..., alias="functionName")
    parameters: dict[str, Any] = Field(default_factory=dict)
    call_id: str = Field(..., alias="callId")
    
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True
    )


class VapiWebhookEvent(BaseModel):
    """
    Webhook event from Vapi.
    
    Vapi sends various event types:
    - function-call: AI wants to execute a tool
    - call-start: New call initiated
    - call-end: Call completed
    - transcript: Real-time transcription
    - hang: Call disconnected
    - speech-update: Partial speech recognition
    """
    type: str
    call_id: str | None = Field(None, alias="callId")
    timestamp: str | None = None
    
    # Function call specific fields
    function_name: str | None = Field(None, alias="functionName")
    parameters: dict[str, Any] | None = None
    
    # Transcript specific fields
    transcript: str | None = None
    
    # Call metadata
    call: dict[str, Any] | None = Field(default_factory=dict)
    
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True
    )