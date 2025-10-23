"""
HTTP client for Fontis Water API integration.

This module provides a comprehensive async HTTP client for interacting with
the Fontis Water RestAPI, implementing:
- 15+ API endpoints for customer, delivery, billing, and contract management
- Automatic retry logic for transient failures
- Structured error handling with custom exceptions
- Connection pooling for performance
- Request/response logging

Design decisions:
- httpx.AsyncClient for async operations and connection pooling
- Tenacity for exponential backoff retry logic
- Custom exceptions for domain-specific error handling
- Centralized _request method for DRY principle
"""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings
from src.core.exceptions import (
    AuthenticationError,
    CustomerNotFoundError,
    FontisAPIError,
    RateLimitError,
    RequestTimeoutError,
)


class FontisClient:
    """
    Async HTTP client for Fontis Water API.
    
    Provides methods for all Fontis API operations including:
    - Customer search and management
    - Delivery scheduling and tracking
    - Invoice and payment history
    - Contract information
    - Product catalog access
    
    Features:
    - Connection pooling (via httpx.AsyncClient)
    - Automatic retry with exponential backoff
    - Structured error handling
    - Request/response logging
    
    Usage:
        client = FontisClient()
        try:
            customers = await client.search_customers("John Doe")
        finally:
            await client.close()
    
    Note: In FastAPI, use the get_fontis_client dependency instead
    of creating clients directly to enable connection pooling.
    """
    
    def __init__(self):
        """
        Initialize Fontis API client.
        
        Creates an httpx.AsyncClient with:
        - Base URL from configuration
        - Authorization header with API key
        - Timeout settings
        - Connection pooling
        """
        self.base_url = settings.fontis_base_url
        self.api_key = settings.fontis_api_key
        self.headers = {
            "X-API-Key": self.api_key,  # Fontis uses X-API-Key header
            "Content-Type": "application/json",
        }
        
        # Create async client with connection pooling
        # Why AsyncClient? Reuses connections, improving performance
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=settings.fontis_timeout
        )
    
    @retry(
        # Retry on specific transient errors
        retry=retry_if_exception_type((RequestTimeoutError, RateLimitError)),
        # Stop after configured number of attempts
        stop=stop_after_attempt(settings.fontis_max_retries + 1),
        # Exponential backoff: 1s, 2s, 4s, 8s...
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True  # Re-raise exception after all retries exhausted
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Make HTTP request to Fontis API with retry logic.
        
        This is the core request method used by all endpoint methods.
        It handles:
        - HTTP request execution
        - Error classification (transient vs permanent)
        - Custom exception raising
        - Response parsing
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/customers/search")
            params: Query parameters
            json_data: JSON request body
        
        Returns:
            Parsed JSON response
        
        Raises:
            AuthenticationError: Invalid API key (401)
            CustomerNotFoundError: Resource not found (404)
            RateLimitError: Rate limit exceeded (429) - retryable
            RequestTimeoutError: Request timed out - retryable
            FontisAPIError: Other API errors
        
        Retry behavior:
        - Timeouts: Retry with exponential backoff
        - Rate limits: Retry with exponential backoff
        - 401/404: Don't retry (permanent errors)
        - 5xx: Don't retry (server errors, likely need investigation)
        """
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            # HTTP error responses (4xx, 5xx)
            if e.response.status_code == 401:
                raise AuthenticationError(
                    "Fontis API authentication failed - check API key",
                    details={"response": e.response.text}
                )
            elif e.response.status_code == 404:
                raise CustomerNotFoundError(
                    "Resource not found",
                    details={"endpoint": endpoint}
                )
            elif e.response.status_code == 429:
                # Rate limit - extract retry-after if provided
                retry_after = e.response.headers.get("Retry-After")
                raise RateLimitError(
                    "Fontis API rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else 60
                )
            else:
                raise FontisAPIError(
                    f"Fontis API error: {e.response.status_code}",
                    status_code=e.response.status_code,
                    details={"response": e.response.text[:500]}
                )
                
        except httpx.TimeoutException as e:
            # Request timeout - retryable
            raise RequestTimeoutError(
                f"Request to {endpoint} timed out after {settings.fontis_timeout}s",
                timeout=settings.fontis_timeout
            )
            
        except httpx.RequestError as e:
            # Connection errors, DNS failures, etc.
            raise FontisAPIError(
                f"Request failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )
    
    # ===== Customer Endpoints =====
    
    async def search_customers(
        self,
        lookup: str,
        offset: int = 0,
        take: int = 25
    ) -> dict[str, Any]:
        """
        Search for customers by name, address, phone, or account number.
        
        Fontis API: POST /api/v1/customers/search
        Tool ID: 41a59e7eacc6c58f0e215dedfc650935
        Method: GetCustomersByName
        
        Args:
            lookup: Search query (name, address, phone, account number)
            offset: Pagination offset (default: 0)
            take: Number of results (default: 25, max: 100)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data.data: List of customer results
            - data.meta: Result metadata
            - meta.pagination: Pagination info
        
        Notes:
            - Returns empty list if no matches found
            - May return multiple matches - verify with address + name
            - Search is case-insensitive
        """
        payload = {
            "lookup": lookup,
            "paginationSettings": {
                "Descending": False,
                "Offset": offset,
                "OrderBy": None,
                "SearchText": "",
                "Take": min(take, 100)
            }
        }
        
        response = await self._request(
            "POST",
            "/customers/search",
            json_data=payload
        )
        return response
    
    async def get_customer_details(
        self,
        customer_id: str,
        include_inactive: bool = False
    ) -> dict[str, Any]:
        """
        Get detailed customer information by account number.
        
        Fontis API: POST /api/v1/customers/details
        Tool ID: b3846a9ea8aee18743363699e0aaa399
        Method: GetCustomerDetails
        
        Args:
            customer_id: Customer account number (customerId)
            include_inactive: Include inactive accounts (default: False)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: Single customer record
        
        Use when:
            - Customer provides account number directly
            - Need verified account record without search
        """
        payload = {
            "includeInactive": include_inactive
        }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}",
            json_data=payload
        )
        return response
    
    async def get_delivery_stops(
        self,
        customer_id: str,
        offset: int = 0,
        take: int = 25
    ) -> dict[str, Any]:
        """
        Get all delivery stops (locations) for a customer.
        
        Fontis API: POST /api/v1/customers/deliverystops
        Tool ID: a8ff151f77354ae30d328f4042b7ab15
        
        Args:
            customer_id: Customer account number
            offset: Pagination offset (default: 0)
            take: Number of results (default: 25, max: 100)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data.deliveryStops: List of delivery stops
            - data.summary: Summary with totalDue, routes, etc.
        
        Notes:
            - Most customers have 1 stop
            - Multiple stops are edge cases (campus, multi-building)
            - deliveryId is required for nearly all delivery operations
        """
        payload = {
            "offset": offset,
            "take": min(take, 100)
        }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/deliveries",
            json_data=payload
        )
        return response
    
    async def get_customer_finance_info(
        self,
        customer_id: str,
        delivery_id: str
    ) -> dict[str, Any]:
        """
        Get combined finance and delivery snapshot for a delivery stop.
        
        Fontis API: POST /api/v1/customers/financedeliveryinfo
        Tool ID: 68b967f63fb242cde93fbbc6e77b9752
        
        Args:
            customer_id: Customer account number
            delivery_id: Delivery stop ID
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data.customerInfo: Financial summary (balance, last payment, etc.)
            - data.deliveryInfo: Delivery details (route, day, equipment, etc.)
        
        Use when:
            - Need account summary for customer conversation
            - Answering "what's my balance and next delivery?"
        """
        payload = {
                "deliveryId": delivery_id
            }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/finance-info",
            json_data=payload
        )
        return response
    
    # ===== Invoice Endpoints =====
    
    async def get_invoice_history(
        self,
        customer_id: str,
        delivery_id: str,
        number_of_months: int = 12,
        offset: int = 0,
        take: int = 25,
        descending: bool = True
    ) -> dict[str, Any]:
        """
        Get invoice and payment history for a delivery stop.
        
        Fontis API: POST /api/v1/customers/invoices
        Tool ID: aebb0c9d5881f619f77819b48aec5b53
        Method: GetCustomerInvoiceAndPaymentHistory
        
        Args:
            customer_id: Customer account number
            delivery_id: Delivery stop ID
            number_of_months: Months of history (default: 12, max: 24)
            offset: Pagination offset (default: 0)
            take: Number of results (default: 25, max: 100)
            descending: Sort newest first (default: True)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data.data: List of invoices and payments
            - data.meta: Result metadata
            - meta.pagination: Pagination info
        
        Notes:
            - Returns both invoices (isInvoice=true) and payments (isPayment=true)
            - For detailed line items, use get_invoice_detail()
            - Accounts may show multiple invoices per month
        """
        payload = {
            "deliveryId": delivery_id,
            "numberOfMonths": min(number_of_months, 24),
            "paginationSettings": {
                "Descending": descending,
                "Offset": offset,
                "OrderBy": None,
                "SearchText": "",
                "Take": min(take, 100)
            }
        }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/invoices",
            json_data=payload
        )
        return response
    
    async def get_invoice_detail(
        self,
        customer_id: str,
        invoice_key: str,
        invoice_date: str,
        include_signature: bool = False,
        include_payments: bool = False
    ) -> dict[str, Any]:
        """
        Get detailed line items for a specific invoice.
        
        Fontis API: POST /api/v1/customers/invoicedetail
        Tool ID: 75ef81ae69cf762ba58d74c48f18d230
        
        Args:
            customer_id: Customer account number
            invoice_key: Invoice identifier
            invoice_date: Invoice date (YYYY-MM-DD)
            include_signature: Include customer signature (default: False)
            include_payments: Include related payments (default: False)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: Detailed invoice with line items
        
        Notes:
            - Do NOT use with payment invoiceKeys (returns no data)
            - Never offer to email PDF (not supported)
            - Refer to customer service for PDF requests
        """
        payload = {
            "invoiceDate": invoice_date,
            "includeSignature": include_signature,
            "includePayments": include_payments
        }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/invoices/{invoice_key}",
            json_data=payload
        )
        return response
    
    # ===== Balance Endpoints =====
    
    async def get_account_balances(
        self,
        customer_id: str,
        include_inactive: bool = False
    ) -> dict[str, Any]:
        """
        Get customer account balance summary.
        
        Fontis API: POST /api/v1/customers/accountbalances
        Tool ID: cce52d0c5e5f4faa1b0e9cbc8eb420e0
        
        Args:
            customer_id: Customer account number
            include_inactive: Include inactive accounts (default: False)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: Balance details (totalDueBalance, pastDueBalance, etc.)
        
        Use when:
            - Customer asks "what do I owe?"
            - Need top-level balance without invoice details
        """
        payload = {
            "includeInactive": include_inactive
        }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/balances",
            json_data=payload
        )
        return response
    
    # ===== Delivery Endpoints =====
    
    async def get_next_scheduled_delivery(
        self,
        customer_id: str,
        delivery_id: str,
        days_ahead: int = 45
    ) -> dict[str, Any]:
        """
        Get next upcoming scheduled delivery.
        
        Fontis API: POST /api/v1/deliveries/next/{customerId}/{deliveryId}
        Tool ID: 92e47d19800cfe7724e27d11b0ec4f1a
        
        Args:
            customer_id: Customer account number
            delivery_id: Delivery stop ID
            days_ahead: Number of days ahead to search (default: 45, max: 90)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: Next delivery details (date, route, dayOfWeek, etc.)
            - meta: Search range and upcoming deliveries count
        
        Use when:
            - Customer asks "when is my next delivery?"
        
        Notes:
            - Fontis uses 20-business-day delivery rotation (~every 4 weeks)
            - Route day may shift slightly for holidays
            - Will-call customers return no delivery until order is scheduled
        """
        payload = {
            "daysAhead": min(days_ahead, 90)
        }
        
        response = await self._request(
            "POST",
            f"/deliveries/next/{customer_id}/{delivery_id}",
            json_data=payload
        )
        return response
    
    async def get_delivery_schedule(
        self,
        customer_id: str,
        delivery_id: str,
        from_date: str,
        to_date: str
    ) -> list[dict[str, Any]]:
        """
        Get delivery schedule for a date range.
        
        Fontis API: GET /api/v1/customers/deliveryschedule
        Tool ID: 248fa66e8012d7f62a7ca15199a7e67e
        
        Args:
            customer_id: Customer account number
            delivery_id: Delivery stop ID
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        
        Returns:
            List of scheduled deliveries in date range
        
        Notes:
            - Shows regular route deliveries only
            - Does NOT include off-route orders
        """
        response = await self._request(
            "GET",
            "/customers/deliveryschedule",
            params={
                "customerId": customer_id,
                "deliveryId": delivery_id,
                "from": from_date,
                "to": to_date
            }
        )
        return response.get("data", [])
    
    async def get_default_products(
        self,
        customer_id: str,
        delivery_id: str
    ) -> dict[str, Any]:
        """
        Get standing order default products for a delivery stop.
        
        Fontis API: POST /api/v1/customers/defaultproducts
        Tool ID: f24e6d2bc336153c076f0220b45f86b6
        
        Args:
            customer_id: Customer account number
            delivery_id: Delivery stop ID
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: List of default products
            - meta: Summary (totalProducts, activeProducts)
        
        Business logic:
            - quantity = 0: Customer is on SWAP model (exchange empties)
            - quantity > 0: STANDING ORDER (fixed amount each delivery)
        """
        payload = {
            "customerId": customer_id
        }
        
        response = await self._request(
            "POST",
            f"/deliveries/{delivery_id}/defaults",
            json_data=payload
        )
        return response
    
    async def get_last_delivery_orders(
        self,
        customer_id: str,
        delivery_id: str,
        number_of_orders: int = 5
    ) -> dict[str, Any]:
        """
        Get recent off-route delivery orders.
        
        Fontis API: POST /api/v1/customers/lastdeliveryorders
        Tool ID: b4e4f83221662ac8d966ec9e5cc6cfb2
        
        Args:
            customer_id: Customer account number
            delivery_id: Delivery stop ID
            number_of_orders: Number of recent orders (default: 5, max: 50)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: List of delivery orders with products and equipment
            - meta: Summary (totalOrders, totalAmount)
        
        Notes:
            - These are service tickets, not regular route deliveries
            - Does NOT reflect recurring route deliveries or standing orders
            - Off-route deliveries have $25 convenience fee, 3-item minimum
        """
        payload = {
            "deliveryId": delivery_id,
            "numberOfOrders": min(number_of_orders, 50)
        }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/orders",
            json_data=payload
        )
        return response
    
    # ===== Product Endpoints =====
    
    async def get_products(
        self,
        customer_id: str,
        delivery_id: str,
        postal_code: str,
        internet_only: bool = True,
        categories: list[str] | None = None,
        default_products: bool = False,
        offset: int = 0,
        take: int = 25
    ) -> dict[str, Any]:
        """
        Get product catalog and pricing.
        
        Fontis API: POST /api/v1/customers/products
        Tool ID: 2b4ad3fcd9ea0acf476734fc7368524f
        
        Args:
            customer_id: Customer account number
            delivery_id: Delivery stop ID
            postal_code: Postal code for location-based pricing
            internet_only: Show only web-available products (default: True)
            categories: Filter by product categories (e.g., ["Fontis Bottled Water"])
            default_products: Show only default/recommended products (default: False)
            offset: Pagination offset (default: 0)
            take: Number of results (default: 25, max: 100)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data.total: Total products available
            - data.records: List of products with pricing and details
        
        Use when:
            - Customer asks "how much is a case of water?"
            - Need to show available products
        """
        payload = {
            "paginationSettings": {
                "Offset": offset,
                "Take": min(take, 100),
                "Descending": False,
                "OrderBy": "description",
                "SearchText": ""
            },
            "deliveryId": delivery_id,
            "internetOnly": internet_only,
            "includeInactive": False,
            "categories": categories or [],
            "webProspect": "",
            "webProspectCatalogState": 0,
            "postalCode": postal_code,
            "employeeInitials": "",
            "includeHandheld": False,
            "webBanners": [],
            "defaultProducts": default_products,
            "webSettings": "MangoWeb",
            "posAdvPricing": "",
            "inventoryOnly": False
        }
            
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/products",
            json_data=payload
        )
        return response
    
    # ===== Contract Endpoints =====
    
    async def get_customer_contracts(
        self,
        customer_id: str,
        delivery_id: str
    ) -> dict[str, Any]:
        """
        Get customer contracts and service agreements.
        
        Fontis API: POST /api/v1/customers/contracts
        Tool ID: 13e223880330066e44c1f2119c0c5aba
        Method: GetCustomerContracts
        
        Args:
            customer_id: Customer account number
            delivery_id: Delivery stop ID
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: List of contracts with:
                - ContractNumber: Contract identifier
                - ContractType: Agreement type (SA = Service Agreement, etc.)
                - StartingDate/ExpirationDate: Contract dates
                - Duration: Term in months
                - AuthrorizedPerson: Signer (note: API has typo)
                - Documents: List of signed agreements (never send to user)
        
        Business rules:
            - Water-only: Month-to-month, no commitment
            - Equipment rental: 12-month, auto-renewing
            - Early termination: $100 or remaining balance, whichever is greater
        
        Notes:
            - May include signed PDF GUIDs (do not expose via AI)
            - Every customer has at least one contract record
        """
        payload = {
            "deliveryId": delivery_id
        }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/contracts",
            json_data=payload
        )
        return response
    
    # ===== Payment Method Endpoints =====
    
    async def get_billing_methods(
        self,
        customer_id: str,
        include_inactive: bool = False
    ) -> dict[str, Any]:
        """
        Get customer billing/payment methods.
        
        Fontis API: POST /api/v1/customers/billingmethods
        Tool ID: f9b9a1ff6729cf4f69d28d188301b32e
        
        Args:
            customer_id: Customer account number
            include_inactive: Include inactive payment methods (default: False)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: List of payment methods with:
                - Description: e.g., "VISA-3758" (masked)
                - VaultId: Internal reference (never expose to user)
                - PayId: Payment ID (never expose to user)
                - CardExpiration: MMYY format
                - Primary: Default payment method
                - Autopay: Auto billing enabled
        
        Security:
            - Never display or expose Vault IDs or PayIds
            - Only show Description (masked card/ACH info) to users
        """
        payload = {
            "includeInactive": include_inactive
        }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/billing-methods",
            json_data=payload
        )
        return response
    
    async def add_credit_card(
        self,
        customer_id: str,
        first_name: str,
        last_name: str,
        card_nonce: str,
        card_number: str,
        card_expiration: str,
        card_cvv: str,
        address: str,
        city: str,
        state: str,
        postal_code: str,
        country: str = "US",
        email: str = "",
        description: str = "",
        bill_time: int = 1,
        customer_status: int = 3,
        prepaid: bool = False,
        set_autopay: bool = False
    ) -> dict[str, Any]:
        """
        Add and vault a credit card for a customer.
        
        Fontis API: POST /api/v1/customers/creditcards
        
        Args:
            customer_id: Customer account number
            first_name: Cardholder first name
            last_name: Cardholder last name
            card_nonce: Card token from payment gateway
            card_number: Credit card number
            card_expiration: Card expiration (MMYY)
            card_cvv: Card CVV code
            address: Billing address
            city: Billing city
            state: Billing state
            postal_code: Billing postal code
            country: Billing country (default: "US")
            email: Customer email
            description: Card description/label
            bill_time: Billing time preference (default: 1)
            customer_status: Customer status code (default: 3)
            prepaid: Is prepaid account (default: False)
            set_autopay: Enable autopay for this card (default: False)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: Vault details (vaultId, payId, lastFour, etc.)
        
        Security:
            - Card data should be tokenized via payment gateway before calling
            - Never log or store raw card numbers
            - Always use PCI-compliant card tokenization
        
        Notes:
            - Can set as autopay method during addition
            - Requires billing address for verification
            - Returns vaultId and payId for future charges
        """
        payload = {
            "firstName": first_name,
            "lastName": last_name,
            "cardNonce": card_nonce,
            "cardNumber": card_number,
            "cardExpiration": card_expiration,
            "cardCVV": card_cvv,
            "address": address,
            "city": city,
            "state": state,
            "postalCode": postal_code,
            "country": country,
            "email": email,
            "description": description,
            "billTime": bill_time,
            "customerStatus": customer_status,
            "prepaid": prepaid,
            "setAutopay": set_autopay
        }
        
        response = await self._request(
            "POST",
            f"/customers/{customer_id}/credit-cards",
            json_data=payload
        )
        return response
    
    # ===== Delivery Frequency Endpoints =====
    
    async def get_delivery_frequencies(self) -> dict[str, Any]:
        """
        Get available delivery frequency codes.
        
        Fontis API: GET /api/v1/deliveries/frequencies
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: List of frequency options (empty if none configured)
        
        Use when:
            - Customer wants to change delivery frequency
            - Need to display frequency options for rescheduling
        
        Notes:
            - Returns system-configured frequency options
            - Required for rescheduling operations
            - May return empty if no custom frequencies are configured
        """
        response = await self._request(
            "GET",
            "/deliveries/frequencies"
        )
        return response
    
    # ===== Orders Search Endpoints =====
    
    async def search_orders(
        self,
        ticket_number: str | None = None,
        customer_id: str | None = None,
        delivery_id: str | None = None,
        only_open_orders: bool = True,
        web_products_only: bool = False
    ) -> dict[str, Any]:
        """
        Search for orders by various criteria.
        
        Fontis API: POST /api/v1/orders/search
        
        Args:
            ticket_number: Ticket number to search for
            customer_id: Customer account number
            delivery_id: Delivery stop ID
            only_open_orders: Return only open/unposted orders (default: True)
            web_products_only: Return only web-orderable products (default: False)
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: List of orders matching search criteria
        
        Use when:
            - Customer asks about a specific order/ticket
            - Need to find orders by customer or delivery ID
            - Checking for open/pending orders
        
        Notes:
            - At least one search parameter should be provided
            - Returns empty list if no matches found
        """
        payload = {
            "ticketNumber": ticket_number or "",
            "customerId": customer_id or "",
            "deliveryId": delivery_id or "",
            "onlyOpenOrders": only_open_orders,
            "webProductsOnly": web_products_only
        }
        
        response = await self._request(
            "POST",
            "/orders/search",
            json_data=payload
        )
        return response
    
    # ===== Route Endpoints =====
    
    async def get_route_stops(
        self,
        route: str,
        route_date: str,
        account_number: str | None = None
    ) -> dict[str, Any]:
        """
        Get all stops for a specific route and date.
        
        Fontis API: POST /api/v1/routes/stops
        Tool ID: b02a838764b22f83dce17e848fa63884
        
        Args:
            route: Route code (e.g., "19")
            route_date: Route date (YYYY-MM-DD)
            account_number: Optional - filter to specific customer
        
        Returns:
            Complete API response with:
            - success: bool
            - message: str
            - data: List of route stops with invoice and skip data
        
        Business logic:
            - invoiceTotal > 0: Delivery completed
            - skipReason present: Delivery skipped
            - Most common skip: "No Bottles Out"
        
        Use when:
            - Confirming route completion
            - Investigating skipped deliveries
            - Verifying delivery on specific date
        
        Notes:
            - Returns ALL stops on the route for that date
            - Use accountNumber to filter to specific customer
            - skipReason indicates why delivery was not completed
        """
        payload = {
            "routeDate": route_date,
            "route": route
        }
        
        # Only add accountNumber if provided (optional filter)
        if account_number:
            payload["accountNumber"] = account_number
            
        response = await self._request(
            "POST",
            "/routes/stops",
            json_data=payload
        )
        return response
    
    async def close(self) -> None:
        """
        Close the HTTP client and release resources.
        
        Closes all open connections in the connection pool.
        Should be called on application shutdown.
        
        Usage:
            await client.close()
        
        In FastAPI, this is handled automatically by the
        close_fontis_client() function in the shutdown hook.
        """
        await self.client.aclose()
