import calendar
import re
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.core.deps import get_fontis_client
from src.core.security import verify_api_key
from src.schemas.tools import (
    AccountBalanceTool,
    InvoiceHistoryTool,
    BillingMethodsTool,
    ProductsTool,
    InvoiceDetailTool,
    PaymentExpiryAlertTool
)
from src.services.fontis_client import FontisClient
from src.core.exceptions import FontisAPIError

router = APIRouter(prefix="/tools/billing", tags=["tools-billing"])


def _get_value(method: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value from the provided keys."""
    for key in keys:
        if key in method:
            value = method[key]
            if value not in (None, "", "null"):
                return value
        # Support case-insensitive lookups
        lower_key = key.lower()
        for actual_key, actual_val in method.items():
            if actual_key.lower() == lower_key and actual_val not in (None, "", "null"):
                return actual_val
    return None


def _parse_expiration(raw: str | None) -> tuple[date | None, int | None, int | None]:
    """Parse expiration string (MMYY, MM/YYYY, etc.) into a date."""
    if not raw:
        return None, None, None

    digits = re.sub(r"\D", "", raw)
    if len(digits) == 4:  # MMYY
        month = int(digits[:2])
        year = 2000 + int(digits[2:])
    elif len(digits) == 6:  # MMYYYY
        month = int(digits[:2])
        year = int(digits[2:])
    else:
        return None, None, None

    if month < 1 or month > 12:
        return None, None, None

    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day), month, year


@router.post("/balance", dependencies=[Depends(verify_api_key)])
async def get_account_balance(
    params: AccountBalanceTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get customer account balance information.
    
    Tool ID: cce52d0c5e5f4faa1b0e9cbc8eb420e0
    Fontis Endpoint: POST /api/v1/customers/{customerId}/balances
    Method: GetCustomerBalances
    
    Behavior:
    - Returns summary-level balance data (total due, past due, on hold)
    - Data matches top-line "Total Due" shown on invoices
    - combine with Invoice History for detailed transactions
    
    AI Usage Guidelines:
    - Use when confirming what's owed or summarizing account status
    - Explain multiple invoices per month are normal (delivery + equipment)
    - Refer to invoice history for transaction details
    """
    try:
        response = await fontis.get_account_balances(
            customer_id=params.customer_id,
            include_inactive=params.include_inactive
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve balance")
            }
        
        return response
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoice-history", dependencies=[Depends(verify_api_key)])
async def get_invoice_history(
    params: InvoiceHistoryTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get customer invoice and payment history.
    
    Tool ID: aebb0c9d5881f619f77819b48aec5b53
    Fontis Endpoint: POST /api/v1/customers/invoices
    Method: GetCustomerInvoiceAndPaymentHistory
    
    Behavior:
    - Returns both invoices and payments in one list
    - Filter by isInvoice/isPayment to separate
    - Supports pagination and date range filtering
    - Accounts may show multiple invoices per month (delivery + equipment)
    
    AI Usage Guidelines:
    - Use this for "What do I owe?" or "When was my last payment?"
    - For detailed line items, use Invoice Detail endpoint
    - Explain that multiple invoices per month are normal (delivery + equipment rental)
    """
    try:
        response = await fontis.get_invoice_history(
            customer_id=params.customer_id,
            delivery_id=params.delivery_id,
            number_of_months=params.number_of_months,
            offset=params.offset,
            take=params.take,
            descending=params.descending
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve invoice history")
            }
        
        # Extract invoice data
        invoices_data = response.get("data", [])
        pagination = response.get("meta", {}).get("pagination", {})
        
        # Separate invoices and payments
        invoices = [item for item in invoices_data if item.get("isInvoice")]
        payments = [item for item in invoices_data if item.get("isPayment")]
        
        # Format for AI consumption
        formatted_invoices = []
        for invoice in invoices:
            formatted_invoices.append({
                "invoiceNumber": invoice.get("invoiceNumber"),
                "invoiceKey": invoice.get("invoiceKey"),
                "date": invoice.get("date"),
                "amount": invoice.get("amount"),
                "formattedAmount": invoice.get("formattedAmount"),
                "tax": invoice.get("tax"),
                "posted": invoice.get("posted"),
                "viewPdf": invoice.get("viewPdf")
            })
        
        formatted_payments = []
        for payment in payments:
            formatted_payments.append({
                "invoiceNumber": payment.get("invoiceNumber"),
                "date": payment.get("date"),
                "amount": payment.get("amount"),
                "formattedAmount": payment.get("formattedAmount")
            })
        
        return {
            "success": True,
            "message": f"Retrieved {len(invoices_data)} records",
            "data": {
                "invoices": formatted_invoices,
                "payments": formatted_payments,
                "totalInvoices": len(invoices),
                "totalPayments": len(payments)
            },
            "meta": {
                "total": pagination.get("total"),
                "hasMore": pagination.get("hasMore"),
                "returned": len(invoices_data)
            }
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payment-methods", dependencies=[Depends(verify_api_key)])
async def get_payment_methods(
    params: BillingMethodsTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get customer billing/payment methods.
    
    Tool ID: f9b9a1ff6729cf4f69d28d188301b32e
    Fontis Endpoint: POST /api/v1/customers/{customerId}/billing-methods
    
    Behavior:
    - Returns all stored payment methods (credit cards, ACH)
    - Shows masked information only (e.g., VISA-3758)
    - Indicates primary method and autopay status
    
    AI Usage Guidelines:
    - NEVER expose VaultId or PayId to users
    - Only show Description field (already masked)
    - Explain card expiration if approaching
    - Can inform about autopay status
    
    Security: Only shows masked information (last 4 digits).
    Never expose Vault IDs or internal tokens.
    """
    try:
        response = await fontis.get_billing_methods(
            customer_id=params.customer_id,
            include_inactive=params.include_inactive
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve payment methods")
            }
        
        methods = response.get("data", [])
        
        # Format for AI - mask sensitive data (VaultId, PayId)
        formatted_methods = []
        for method in methods:
            formatted_methods.append({
                "description": method.get("Description"),  # e.g., "VISA-3758"
                "cardExpiration": method.get("CardExpiration"),  # MMYY format
                "isPrimary": method.get("Primary", False),
                "isAutopay": method.get("Autopay", False)
            })
        
        return {
            "success": True,
            "message": f"Found {len(methods)} payment method(s)",
            "data": formatted_methods
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payment-expiry-alerts", dependencies=[Depends(verify_api_key)])
async def get_payment_expiry_alerts(
    params: PaymentExpiryAlertTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Detect payment methods that are expired or approaching expiration.

    Tool ID: (new)
    Fontis Endpoint: Uses billing methods data and local date calculations.

    Behavior:
    - Pulls masked payment methods from Fontis
    - Parses expiration dates (MMYY, MM/YYYY, etc.) and computes days remaining
    - Flags methods as expired, expiring soon (<= threshold), or active
    - Returns a summary and per-method detail with no sensitive tokens
    """
    try:
        response = await fontis.get_billing_methods(
            customer_id=params.customer_id,
            include_inactive=params.include_inactive
        )
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not response.get("success"):
        return {
            "success": False,
            "message": response.get("message", "Failed to retrieve billing methods")
        }

    methods = response.get("data", []) or []
    today = date.today()
    threshold = params.days_threshold

    categorized: dict[str, list[dict[str, Any]]] = {
        "expired": [],
        "expiring_soon": [],
        "active": [],
        "no_expiration": [],
    }
    results: list[dict[str, Any]] = []

    for method in methods:
        description = _get_value(method, "description", "Description", "displayName")
        method_type = _get_value(method, "type", "methodType", "paymentType")
        raw_exp = _get_value(method, "cardExpiration", "CardExpiration", "expiration")
        autopay = bool(_get_value(method, "autopay", "AutoPay", "autoPay"))
        primary = bool(_get_value(method, "primary", "Primary"))
        status_flag = _get_value(method, "status", "Status")

        expiration_date, exp_month, exp_year = _parse_expiration(raw_exp)
        days_remaining: int | None = None
        if expiration_date is None:
            status = "no_expiration"
        else:
            days_remaining = (expiration_date - today).days
            if days_remaining < 0:
                status = "expired"
            elif days_remaining <= threshold:
                status = "expiring_soon"
            else:
                status = "active"

        entry = {
            "description": description,
            "type": method_type,
            "status": status,
            "primary": primary,
            "autopay": autopay,
            "rawStatus": status_flag,
            "expiration": {
                "raw": raw_exp,
                "month": exp_month,
                "year": exp_year,
                "isoDate": expiration_date.isoformat() if expiration_date else None,
                "daysRemaining": days_remaining,
            },
            "notes": _get_value(method, "notes", "Notes"),
        }

        categorized[status].append(entry)
        results.append(entry)

    summary = {
        "total": len(methods),
        "expired": len(categorized["expired"]),
        "expiringSoon": len(categorized["expiring_soon"]),
        "active": len(categorized["active"]),
        "unknown": len(categorized["no_expiration"]),
        "thresholdDays": threshold,
    }

    if not methods:
        message = "No payment methods were found for this customer."
    elif summary["expired"]:
        message = f"{summary['expired']} payment method(s) are already expired."
    elif summary["expiringSoon"]:
        message = f"{summary['expiringSoon']} payment method(s) expire within {threshold} days."
    else:
        message = "All payment methods are active and outside the alert window."

    return {
        "success": True,
        "message": message,
        "data": results,
        "summary": summary,
    }


@router.post("/products", dependencies=[Depends(verify_api_key)])
async def get_products(
    params: ProductsTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get product catalog and pricing.
    
    Tool ID: 2b4ad3fcd9ea0acf476734fc7368524f
    Fontis Endpoint: POST /api/v1/customers/{customerId}/products
    
    Behavior:
    - Returns full product catalog with pricing
    - Supports filtering by category (e.g., "Fontis Bottled Water")
    - Shows availability and inventory status
    - Includes product descriptions and unit pricing
    
    AI Usage Guidelines:
    - Use for "How much is a case of water?" or "What products are available?"
    - Filter by categories to narrow results
    - Show formattedPrice field for user-friendly display
    - Explain deposit products and bottle exchanges
    """
    try:
        # customerId is now required per documentation for accurate pricing
        # Fontis API requires customer_id in URL path
        customer_id = params.customer_id
        delivery_id = params.delivery_id or ""
        postal_code = params.postal_code or ""
        
        response = await fontis.get_products(
            customer_id=customer_id,
            delivery_id=delivery_id,
            postal_code=postal_code,
            internet_only=params.internet_only,
            categories=params.categories,
            default_products=params.default_products,
            offset=params.offset,
            take=params.take
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve products")
            }
        
        data = response.get("data", {})
        products = data.get("records", [])
        
        # Format products for AI consumption
        formatted_products = []
        for product in products:
            formatted_products.append({
                "code": product.get("code"),
                "description": product.get("description"),
                "webDescription": product.get("webDescription"),
                "unitDescription": product.get("unitDescription"),
                "price": product.get("defaultPrice"),
                "formattedPrice": product.get("formattedPrice"),
                "category": product.get("productClass"),
                "isAvailable": product.get("isAvailable", True),
                "recurring": product.get("recurring", False),
                "minimumQuantity": product.get("minimumOrderQuantity", 1)
            })
        
        return {
            "success": True,
            "message": f"Found {data.get('total', 0)} products",
            "data": {
                "products": formatted_products,
                "total": data.get("total"),
                "returned": len(products)
            }
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoice-detail", dependencies=[Depends(verify_api_key)])
async def get_invoice_detail(
    params: InvoiceDetailTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get detailed line items for a specific invoice.
    
    Tool ID: 75ef81ae69cf762ba58d74c48f18d230
    Fontis Endpoint: POST /api/v1/customers/{customerId}/invoices/{invoiceKey}
    Method: GetInvoiceDetail
    
    Purpose:
    Retrieve detailed invoice line items for a specific invoice,
    including product descriptions, quantities, unit prices, taxes, and totals.
    
    Behavior:
    - Returns complete invoice header and line item details
    - Includes customer info, billing address, route, driver
    - Shows product-level breakdown with pricing and taxes
    - Optionally includes signature and payment records
    
    AI Usage Guidelines:
    - Use when customer asks for breakdown of what an invoice includes
    - Do NOT use with "Payment" invoiceKeys (returns no data)
    - Never offer to email a PDF; refer to Customer Service if requested
    - Explain product codes and deposits clearly
    - Summarize totals and taxes in user-friendly way
    
    Notes:
    - includeSignature: Adds signature image if captured
    - includePayments: Shows related payment records
    """
    try:
        # Validate that invoiceKey is not a payment record
        # Payment records typically have invoiceKey starting with "Payment" or similar
        invoice_key_lower = params.invoice_key.lower() if params.invoice_key else ""
        if "payment" in invoice_key_lower and invoice_key_lower != "payment":
            # Allow if it's part of a longer key, but check if it's clearly a payment
            if invoice_key_lower.startswith("payment") or invoice_key_lower == "payment":
                return {
                    "success": False,
                    "message": "Invoice detail cannot be retrieved for payment records. Use invoice_history to view payment information."
                }
        
        response = await fontis.get_invoice_detail(
            customer_id=params.customer_id,
            invoice_key=params.invoice_key,
            invoice_date=params.invoice_date,
            include_signature=params.include_signature,
            include_payments=params.include_payments
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve invoice detail")
            }
        
        return response
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

