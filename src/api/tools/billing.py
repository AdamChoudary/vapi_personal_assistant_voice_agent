from fastapi import APIRouter, Depends, HTTPException

from src.core.deps import get_fontis_client
from src.core.security import verify_api_key
from src.schemas.tools import (
    AccountBalanceTool,
    InvoiceHistoryTool,
    BillingMethodsTool,
    ProductsTool,
    InvoiceDetailTool,
    CreditCardVaultTool
)
from src.services.fontis_client import FontisClient
from src.core.exceptions import FontisAPIError

router = APIRouter(prefix="/tools/billing", tags=["tools-billing"])


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


@router.post("/add-credit-card", dependencies=[Depends(verify_api_key)])
async def add_credit_card(
    params: CreditCardVaultTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Add and vault a credit card for a customer.
    
    Fontis Endpoint: POST /api/v1/customers/{customerId}/credit-cards
    Method: CreditCardVaultAdd
    
    Purpose:
    Add and vault a new credit card for recurring or one-time payments.
    Stores card securely in payment vault and can set as autopay method.
    
    Behavior:
    - Tokenizes and vaults card data securely
    - Returns vaultId and payId for future charges
    - Can set as primary payment method
    - Can enable autopay during addition
    - Requires billing address for verification
    
    Security:
    - Card data should be tokenized via payment gateway before calling
    - Never log or store raw card numbers
    - Always use PCI-compliant card tokenization
    - Only masked information (last 4 digits) returned
    
    AI Usage Guidelines:
    - Use when customer wants to add a payment method
    - Explain that card will be securely stored
    - Confirm autopay status if requested
    - Never display full card numbers
    - Refer to Customer Service for card security questions
    
    Notes:
    - Requires complete billing address
    - Card expiration format: MMYY
    - Returns success with vaultId or error with failure reason
    """
    try:
        response = await fontis.add_credit_card(
            customer_id=params.customer_id,
            first_name=params.first_name,
            last_name=params.last_name,
            card_nonce=params.card_nonce,
            card_number=params.card_number,
            card_expiration=params.card_expiration,
            card_cvv=params.card_cvv,
            address=params.address,
            city=params.city,
            state=params.state,
            postal_code=params.postal_code,
            country=params.country,
            email=params.email,
            description=params.description,
            bill_time=params.bill_time,
            customer_status=params.customer_status,
            prepaid=params.prepaid,
            set_autopay=params.set_autopay
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to add credit card")
            }
        
        # Mask sensitive data in response
        data = response.get("data", {})
        return {
            "success": True,
            "message": "Credit card added successfully",
            "data": {
                "lastFour": data.get("lastFour"),
                "description": f"{params.description} (ending in {data.get('lastFour')})",
                "autopayEnabled": params.set_autopay
            }
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))
