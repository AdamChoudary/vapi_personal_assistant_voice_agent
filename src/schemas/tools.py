"""
Pydantic schemas for Vapi tool/function parameters.

This module defines request models for all tool endpoints.
Each tool corresponds to a Vapi function that can be called
during voice conversations.

Design decisions:
- Use Field aliases for flexible parameter names (camelCase/snake_case)
- Comprehensive descriptions for Vapi function definitions
- Type validation at API boundary
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolParameter(BaseModel):
    """Tool parameter definition for Vapi function schemas."""
    type: str
    description: str
    enum: list[str] | None = None
    required: bool = False


class ToolDefinition(BaseModel):
    """
    Vapi tool/function definition schema.
    
    Used to register functions with Vapi assistant.
    """
    type: str = "function"
    function: dict[str, Any] = Field(
        default_factory=lambda: {
            "name": "",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    )


# ===== Customer Tool Parameters =====


class CustomerSearchTool(BaseModel):
    """
    Parameters for customer search tool.
    
    Tool ID: 41a59e7eacc6c58f0e215dedfc650935
    Endpoint: POST /tools/customer/search
    
    Note: lookup is REQUIRED - this forces VAPI to extract parameter before calling
    """
    lookup: str = Field(
        ...,
        min_length=1,
        description="Customer name, address, phone, or account number to search for"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset"
    )
    take: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Number of results to return (max 100)"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class CustomerSearchCompatTool(BaseModel):
    """
    Compatibility schema for VAPI dashboard tests that may send
    {"query", "pageLimit", "locationId"}. We map query→lookup.
    """
    lookup: str | None = Field(default=None, description="Primary search term")
    query: str | None = Field(default=None, description="Alias for lookup from dashboard body")
    pageLimit: int | None = Field(default=None, description="Ignored; accepted for compatibility")
    locationId: str | None = Field(default=None, description="Ignored; accepted for compatibility")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    take: int = Field(default=25, ge=1, le=100, description="Page size")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class CustomerDetailsTool(BaseModel):
    """
    Parameters for customer details tool.
    
    Tool ID: b3846a9ea8aee18743363699e0aaa399
    Endpoint: POST /tools/customer/details
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    include_inactive: bool = Field(
        default=False,
        description="Include inactive customers in results"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class DeliveryStopsTool(BaseModel):
    """
    Parameters for delivery stops tool.
    
    Tool ID: a8ff151f77354ae30d328f4042b7ab15
    Endpoint: POST /tools/delivery/stops
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset"
    )
    take: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Number of results to return (max 100)"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class FinanceDeliveryInfoTool(BaseModel):
    """
    Parameters for finance and delivery info tool.
    
    Tool ID: 68b967f63fb242cde93fbbc6e77b9752
    Endpoint: POST /tools/customer/finance-info
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    delivery_id: str | None = Field(
        default=None,
        alias="deliveryId",
        description="Delivery stop ID (optional, will use primary if not provided)"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Delivery Tool Parameters =====


class NextDeliveryTool(BaseModel):
    """
    Parameters for next delivery and default products tools.
    
    Used by:
    - Tool ID: 92e47d19800cfe7724e27d11b0ec4f1a (next delivery)
    - Tool ID: f24e6d2bc336153c076f0220b45f86b6 (default products)
    
    Endpoints:
    - POST /tools/delivery/next-scheduled
    - POST /tools/delivery/default-products
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    delivery_id: str = Field(
        ...,
        alias="deliveryId",
        description="Delivery stop ID (from get_delivery_stops)"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Billing Tool Parameters =====


class InvoiceHistoryTool(BaseModel):
    """
    Parameters for invoice history tool.
    
    Tool ID: aebb0c9d5881f619f77819b48aec5b53
    Endpoint: POST /tools/billing/invoice-history
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    delivery_id: str = Field(
        ...,
        alias="deliveryId",
        description="Delivery stop ID"
    )
    number_of_months: int = Field(
        default=12,
        alias="numberOfMonths",
        ge=1,
        le=24,
        description="Number of months of history to retrieve (max 24)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset"
    )
    take: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Number of results to return (max 100)"
    )
    descending: bool = Field(
        default=True,
        description="Sort order (True = newest first)"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class AccountBalanceTool(BaseModel):
    """
    Parameters for account balance tool.
    
    Tool ID: cce52d0c5e5f4faa1b0e9cbc8eb420e0
    Endpoint: POST /tools/billing/balance
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    include_inactive: bool = Field(
        default=False,
        alias="includeInactive",
        description="Include inactive accounts"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class BillingMethodsTool(BaseModel):
    """
    Parameters for billing methods tool.
    
    Tool ID: f9b9a1ff6729cf4f69d28d188301b32e
    Endpoint: POST /tools/billing/payment-methods
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    include_inactive: bool = Field(
        default=False,
        alias="includeInactive",
        description="Include inactive payment methods"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class ProductsTool(BaseModel):
    """
    Parameters for products catalog tool.
    
    Tool ID: 2b4ad3fcd9ea0acf476734fc7368524f
    Endpoint: POST /tools/billing/products
    """
    customer_id: str | None = Field(
        default=None,
        alias="customerId",
        description="Customer account number (optional)"
    )
    delivery_id: str | None = Field(
        default=None,
        alias="deliveryId",
        description="Delivery stop ID (optional)"
    )
    postal_code: str | None = Field(
        default=None,
        alias="postalCode",
        description="Postal code for pricing (optional)"
    )
    internet_only: bool = Field(
        default=True,
        alias="internetOnly",
        description="Show only internet-available products"
    )
    categories: list[str] = Field(
        default=[],
        description="Filter by product categories"
    )
    default_products: bool = Field(
        default=False,
        alias="defaultProducts",
        description="Show only default/recommended products"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset"
    )
    take: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Number of results to return (max 100)"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Contracts Tool Parameters =====


class ContractsTool(BaseModel):
    """
    Parameters for contracts tool.
    
    Tool ID: 13e223880330066e44c1f2119c0c5aba
    Endpoint: POST /tools/contracts/get-contracts
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    delivery_id: str = Field(
        ...,
        alias="deliveryId",
        description="Delivery stop ID"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Invoice Detail Tool Parameters =====


class InvoiceDetailTool(BaseModel):
    """
    Parameters for invoice detail tool.
    
    Tool ID: 75ef81ae69cf762ba58d74c48f18d230
    Endpoint: POST /tools/billing/invoice-detail
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    invoice_key: str = Field(
        ...,
        alias="invoiceKey",
        description="Invoice key/identifier"
    )
    invoice_date: str = Field(
        ...,
        alias="invoiceDate",
        description="Invoice date (YYYY-MM-DD)"
    )
    include_signature: bool = Field(
        default=False,
        alias="includeSignature",
        description="Include customer signature"
    )
    include_payments: bool = Field(
        default=False,
        alias="includePayments",
        description="Include related payments"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Default Products Updated Tool Parameters =====


class DefaultProductsTool(BaseModel):
    """
    Parameters for default products tool.
    
    Tool ID: f24e6d2bc336153c076f0220b45f86b6
    Endpoint: POST /tools/delivery/default-products
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    delivery_id: str = Field(
        ...,
        alias="deliveryId",
        description="Delivery stop ID"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Next Scheduled Delivery Updated Tool Parameters =====


class NextScheduledDeliveryTool(BaseModel):
    """
    Parameters for next scheduled delivery tool.
    
    Tool ID: 92e47d19800cfe7724e27d11b0ec4f1a
    Endpoint: POST /tools/delivery/next-scheduled
    """
    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Customer account number"
    )
    delivery_id: str = Field(
        ...,
        alias="deliveryId",
        description="Delivery stop ID"
    )
    days_ahead: int = Field(
        default=45,
        alias="daysAhead",
        ge=1,
        le=90,
        description="Number of days ahead to search (default: 45, max: 90)"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Orders Search Tool Parameters =====


class OrdersSearchTool(BaseModel):
    """
    Parameters for orders search tool.
    
    Endpoint: POST /tools/orders/search
    """
    ticket_number: str | None = Field(
        default=None,
        alias="ticketNumber",
        description="Ticket number to search for"
    )
    customer_id: str | None = Field(
        default=None,
        alias="customerId",
        description="Customer account number"
    )
    delivery_id: str | None = Field(
        default=None,
        alias="deliveryId",
        description="Delivery stop ID"
    )
    only_open_orders: bool = Field(
        default=True,
        alias="onlyOpenOrders",
        description="Return only open/unposted orders"
    )
    web_products_only: bool = Field(
        default=False,
        alias="webProductsOnly",
        description="Return only web-orderable products"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Route Stops Tool Parameters =====


class RouteStopsTool(BaseModel):
    """
    Parameters for route stops tool.
    
    Tool ID: b02a838764b22f83dce17e848fa63884
    Endpoint: POST /tools/routes/stops
    """
    route_date: str = Field(
        ...,
        alias="routeDate",
        description="Route date (YYYY-MM-DD)"
    )
    route: str = Field(
        ...,
        description="Route code (e.g., '19')"
    )
    account_number: str | None = Field(
        default=None,
        alias="accountNumber",
        description="Optional - filter to specific customer account"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Onboarding Tool Parameters =====


class SendContractTool(BaseModel):
    """
    Parameters for sending onboarding contract tool.
    
    Tool ID: TBD
    Endpoint: POST /tools/onboarding/send-contract
    """
    customer_name: str = Field(
        ...,
        alias="customerName",
        min_length=2,
        description="Full customer name"
    )
    email: str = Field(
        ...,
        description="Customer email address"
    )
    phone: str = Field(
        ...,
        description="Customer phone number (E.164 format recommended)"
    )
    address: str = Field(
        ...,
        description="Street address"
    )
    city: str = Field(
        ...,
        description="City name"
    )
    state: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="State/Province code (2 letters)"
    )
    postal_code: str = Field(
        ...,
        alias="postalCode",
        description="ZIP/Postal code"
    )
    delivery_preference: str | None = Field(
        default=None,
        alias="deliveryPreference",
        description="Preferred delivery day (e.g., 'Tuesday')"
    )
    send_email: bool = Field(
        default=True,
        alias="sendEmail",
        description="Whether to send contract via email (default: True)"
    )
    
    model_config = ConfigDict(populate_by_name=True)


class ContractStatusTool(BaseModel):
    """
    Parameters for checking onboarding contract submission status.
    
    Endpoint: POST /tools/onboarding/contract-status
    """
    submission_id: str = Field(
        ...,
        alias="submissionId",
        description="JotForm submission ID from send_contract response"
    )
    
    model_config = ConfigDict(populate_by_name=True)


# ===== Outbound Call Tool Parameters =====


class DeclinedPaymentCallTool(BaseModel):
    """Parameters for declined payment outbound call."""

    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Fontis customer ID"
    )
    customer_phone: str = Field(
        ...,
        alias="customerPhone",
        description="Customer phone number (E.164 format)"
    )
    customer_name: str = Field(
        ...,
        alias="customerName",
        description="Customer full name"
    )
    declined_amount: float | None = Field(
        default=None,
        alias="declinedAmount",
        description="Amount that was declined"
    )
    account_balance: float | None = Field(
        default=None,
        alias="accountBalance",
        description="Current account balance"
    )

    model_config = ConfigDict(populate_by_name=True)


class CollectionsCallTool(BaseModel):
    """Parameters for collections outbound call."""

    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Fontis customer ID"
    )
    customer_phone: str = Field(
        ...,
        alias="customerPhone",
        description="Customer phone number (E.164 format)"
    )
    customer_name: str = Field(
        ...,
        alias="customerName",
        description="Customer full name"
    )
    past_due_amount: float = Field(
        ...,
        alias="pastDueAmount",
        description="Past due amount"
    )
    days_past_due: int | None = Field(
        default=None,
        alias="daysPastDue",
        description="Days the account is past due"
    )

    model_config = ConfigDict(populate_by_name=True)


class DeliveryReminderCallTool(BaseModel):
    """Parameters for delivery reminder outbound call or SMS."""

    customer_id: str = Field(
        ...,
        alias="customerId",
        description="Fontis customer ID"
    )
    customer_phone: str = Field(
        ...,
        alias="customerPhone",
        description="Customer phone number (E.164 format)"
    )
    customer_name: str = Field(
        ...,
        alias="customerName",
        description="Customer full name"
    )
    delivery_date: str = Field(
        ...,
        alias="deliveryDate",
        description="Scheduled delivery date (YYYY-MM-DD)"
    )
    send_sms: bool = Field(
        default=False,
        alias="sendSms",
        description="Send SMS instead of placing a call"
    )
    account_on_hold: bool = Field(
        default=False,
        alias="accountOnHold",
        description="Account is past due/on hold"
    )

    model_config = ConfigDict(populate_by_name=True)
