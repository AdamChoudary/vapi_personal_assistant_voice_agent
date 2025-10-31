from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response

from src.core.deps import get_fontis_client
from src.core.security import verify_api_key
from src.schemas.tools import CustomerSearchTool, CustomerSearchCompatTool, CustomerDetailsTool, FinanceDeliveryInfoTool
from src.services.fontis_client import FontisClient
from src.services.cache import customer_search_cache
from src.core.exceptions import CustomerNotFoundError, FontisAPIError

router = APIRouter(prefix="/tools/customer", tags=["tools-customer"])


@router.post("/search", dependencies=[Depends(verify_api_key)])
async def search_customer(
    params: CustomerSearchTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Search for customers by name, address, or account number.
    
    Tool ID: 41a59e7eacc6c58f0e215dedfc650935
    Fontis Endpoint: POST /api/v1/customers/search
    Method: GetCustomersByName
    
    Behavior:
    - Returns multiple matches (if found)
    - Includes contact info, address, financial summary
    - Supports pagination for large result sets
    
    AI Usage Guidelines:
    - Ask for service address first
    - If multiple results: ask for name confirmation
    - Confirm at least 2 identifiers before proceeding (address + name)
    """
    try:
        # lookup is now required at schema level (VAPI forced to extract)
        # Just validate it's not empty string
        if params.lookup.strip() == "":
            return {
                "result": "Search term cannot be empty. Please provide a customer name, phone, address, or account number."
            }
        
        # Check cache first (speeds up VAPI calls from 5s to < 1s)
        cache_key = f"search:{params.lookup}:{params.offset}:{params.take}"
        cached_result = customer_search_cache.get(cache_key)
        
        if cached_result is not None:
            # Return cached result immediately
            return cached_result
        
        # Call Fontis API with actual structure
        response = await fontis.search_customers(
            lookup=params.lookup,
            offset=params.offset,
            take=params.take
        )
        
        # Check if search was successful
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Search failed"),
                "data": []
            }
        
        # Extract customer data
        customers = response.get("data", {}).get("data", [])
        pagination = response.get("meta", {}).get("pagination", {})
        
        if not customers:
            return {
                "result": "No customers found matching your search. Please try a different name, phone, address, or account number."
            }
        
        # Return minimal plain text for SPEED (VAPI has ~5 second timeout)
        # Only return first 3 customers to keep response fast
        count = len(customers)
        customers_to_show = customers[:3]
        
        result_parts = [f"Found {count} customer(s):"]
        
        for idx, customer in enumerate(customers_to_show, 1):
            name = customer.get('name', 'Unknown')
            cust_id = customer.get('customerId', '')
            address = customer.get("address", {}).get("fullAddress", "")
            phone = customer.get("contact", {}).get("phoneNumber", "")
            
            result_parts.append(f"\n{idx}. {name} (ID: {cust_id})")
            if address:
                result_parts.append(f"   {address}")
            if phone:
                result_parts.append(f"   Phone: {phone}")
        
        if count > 3:
            result_parts.append(f"\n...and {count - 3} more customers.")
        
        result_parts.append("\nUse the Customer ID to get more details.")
        
        # Return as JSON with "result" field for VAPI
        result = {
            "result": "\n".join(result_parts)
        }
        
        # Cache for 60 seconds to speed up repeated searches
        customer_search_cache.set(cache_key, result)
        
        return result
        
    except CustomerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-text", dependencies=[Depends(verify_api_key)], response_class=PlainTextResponse)
async def search_customer_text(
    params: CustomerSearchTool,
    fontis: FontisClient = Depends(get_fontis_client)
):
    """
    Text-only variant for VAPI compatibility. Returns plain text response.
    """
    try:
        if params.lookup.strip() == "":
            return "Search term cannot be empty. Please provide a customer name, phone, address, or account number."

        cache_key = f"search-text:{params.lookup}:{params.offset}:{params.take}"
        cached = customer_search_cache.get(cache_key)
        if cached is not None and isinstance(cached, dict) and "result" in cached:
            return cached["result"]

        response = await fontis.search_customers(
            lookup=params.lookup,
            offset=params.offset,
            take=params.take
        )

        if not response.get("success"):
            return response.get("message", "Search failed")

        customers = response.get("data", {}).get("data", [])
        if not customers:
            return "No customers found matching your search. Please try a different name, phone, address, or account number."

        count = len(customers)
        customers_to_show = customers[:3]
        result_parts = [f"Found {count} customer(s):", ""]

        for idx, customer in enumerate(customers_to_show, 1):
            name = customer.get('name', 'Unknown')
            cust_id = customer.get('customerId', '')
            address = customer.get("address", {}).get("fullAddress", "")
            phone = customer.get("contact", {}).get("phoneNumber", "")

            result_parts.append(f"{idx}. {name} (ID: {cust_id})")
            if address:
                result_parts.append(f"   {address}")
            if phone:
                result_parts.append(f"   Phone: {phone}")
            result_parts.append("")

        if count > 3:
            result_parts.append(f"...and {count - 3} more customers.")

        result_parts.append("Use the Customer ID to get more details.")

        text_result = "\n".join(result_parts)
        customer_search_cache.set(cache_key, {"result": text_result})
        return text_result
        
    except CustomerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-vapi", dependencies=[Depends(verify_api_key)])
async def search_customer_vapi(
    params: CustomerSearchCompatTool,
    fontis: FontisClient = Depends(get_fontis_client)
):
    """
    VAPI-optimized: returns plain text with identity encoding to avoid proxy compression/chunking.
    """
    try:
        effective_lookup = (params.lookup or params.query or "").strip()
        if effective_lookup == "":
            body = "Search term cannot be empty. Please provide a customer name, phone, address, or account number."
            return Response(content=body.encode("utf-8"), media_type="text/plain; charset=utf-8", headers={
                "Content-Encoding": "identity",
                "Cache-Control": "no-transform"
            })

        cache_key = f"search-vapi:{effective_lookup}:{params.offset}:{params.take}"
        cached = customer_search_cache.get(cache_key)
        if cached is not None and isinstance(cached, dict) and "result" in cached:
            body = cached["result"].encode("utf-8")
            return Response(content=body, media_type="text/plain; charset=utf-8", headers={
                "Content-Encoding": "identity",
                "Cache-Control": "no-transform"
            })

        response = await fontis.search_customers(
            lookup=effective_lookup,
            offset=params.offset,
            take=params.take
        )

        if not response.get("success"):
            body = response.get("message", "Search failed")
            return Response(content=body.encode("utf-8"), media_type="text/plain; charset=utf-8", headers={
                "Content-Encoding": "identity",
                "Cache-Control": "no-transform"
            })

        customers = response.get("data", {}).get("data", [])
        if not customers:
            body = "No customers found matching your search. Please try a different name, phone, address, or account number."
            return Response(content=body.encode("utf-8"), media_type="text/plain; charset=utf-8", headers={
                "Content-Encoding": "identity",
                "Cache-Control": "no-transform"
            })

        count = len(customers)
        customers_to_show = customers[:3]
        parts = [f"Found {count} customer(s):", ""]
        for idx, customer in enumerate(customers_to_show, 1):
            name = customer.get('name', 'Unknown')
            cust_id = customer.get('customerId', '')
            address = customer.get("address", {}).get("fullAddress", "")
            phone = customer.get("contact", {}).get("phoneNumber", "")
            parts.append(f"{idx}. {name} (ID: {cust_id})")
            if address:
                parts.append(f"   {address}")
            if phone:
                parts.append(f"   Phone: {phone}")
            parts.append("")

        if count > 3:
            parts.append(f"...and {count - 3} more customers.")
        parts.append("Use the Customer ID to get more details.")

        body_str = "\n".join(parts)
        customer_search_cache.set(cache_key, {"result": body_str})
        return Response(content=body_str.encode("utf-8"), media_type="text/plain; charset=utf-8", headers={
            "Content-Encoding": "identity",
            "Cache-Control": "no-transform"
        })
        
    except CustomerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/details", dependencies=[Depends(verify_api_key)])
async def get_customer_details(
    params: CustomerDetailsTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get detailed customer information by account number.
    
    Tool ID: b3846a9ea8aee18743363699e0aaa399
    Fontis Endpoint: POST /api/v1/customers/details
    Method: GetCustomerDetails
    
    Use Case:
    - Customer provides their account number (printed on invoices)
    - Faster than search when account number is known
    - Returns same data structure as search
    
    AI Guidelines:
    - Confirm name or address for verification
    - This avoids fuzzy search when exact account is known
    """
    try:
        response = await fontis.get_customer_details(params.customer_id)
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Customer not found")
            }
        
        customer = response.get("data", {})
        
        return {
            "success": True,
            "message": "Customer details retrieved successfully",
            "data": {
                "customerId": customer.get("customerId"),
                "name": customer.get("name"),
                "address": customer.get("address", {}).get("fullAddress"),
                "addressDetails": {
                    "street": customer.get("address", {}).get("street"),
                    "city": customer.get("address", {}).get("city"),
                    "state": customer.get("address", {}).get("state"),
                    "postalCode": customer.get("address", {}).get("postalCode")
                },
                "phone": customer.get("contact", {}).get("phoneNumber"),
                "email": customer.get("contact", {}).get("emailAddress"),
                "totalDue": customer.get("financial", {}).get("totalDue", 0.0),
                "hasScheduledDeliveries": customer.get("financial", {}).get("hasScheduledDeliveries", False)
            }
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/finance-info", dependencies=[Depends(verify_api_key)])
async def get_finance_delivery_info(
    params: FinanceDeliveryInfoTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get combined finance and delivery information for a customer.
    
    Tool ID: 68b967f63fb242cde93fbbc6e77b9752
    Fontis Endpoint: POST /api/v1/customers/{customerId}/finance-info
    
    Behavior:
    - Returns comprehensive snapshot of billing and delivery data
    - Includes current balance, last payment, next delivery, equipment
    - Combines financial and operational data in single call
    
    AI Usage Guidelines:
    - Use for "What do I owe?" or "When is my next delivery?"
    - Shows last payment date and amount
    - Displays equipment on site (coolers, dispensers)
    - Includes route day and scheduling area
    """
    try:
        # If delivery_id not provided, get customer's primary delivery
        delivery_id = params.delivery_id
        if not delivery_id:
            # Get customer details to find their delivery IDs
            customer = await fontis.get_customer_details(params.customer_id)
            if customer.get("success") and customer.get("data"):
                # Try to get first delivery ID from customer data
                deliveries = customer["data"].get("deliveries", [])
                if deliveries:
                    delivery_id = deliveries[0].get("deliveryId")
        
        if not delivery_id:
            return {
                "success": False,
                "message": "Unable to find delivery information for this customer. They may not have any active deliveries set up."
            }
        
        response = await fontis.get_customer_finance_info(
            customer_id=params.customer_id,
            delivery_id=delivery_id
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve finance info")
            }
        
        data = response.get("data", {})
        customer_info = data.get("customerInfo", {})
        delivery_info = data.get("deliveryInfo", {})
        
        return {
            "success": True,
            "message": "Finance and delivery info retrieved successfully",
            "data": {
                "financial": {
                    "currentBalance": customer_info.get("currentBalance"),
                    "formattedBalance": customer_info.get("formattedCurrentBalance"),
                    "pastDue": customer_info.get("pastDue"),
                    "formattedPastDue": customer_info.get("formattedPastDue"),
                    "hasPastDue": customer_info.get("hasPastDue"),
                    "oldestInvoiceDate": customer_info.get("oldest"),
                    "lastPayment": customer_info.get("lastPayment"),
                    "paymentMethod": customer_info.get("creditCard")
                },
                "delivery": {
                    "deliveryId": delivery_info.get("deliveryId"),
                    "deliveryName": delivery_info.get("deliveryName"),
                    "address": delivery_info.get("deliveryAddress"),
                    "route": delivery_info.get("routeCode"),
                    "routeDay": delivery_info.get("routeDay"),
                    "nextDeliveryDate": delivery_info.get("nextDeliveryDate"),
                    "schedulingArea": delivery_info.get("schedulingArea"),
                    "hasScheduledDeliveries": delivery_info.get("hasScheduledDeliveries"),
                    "tankInfo": delivery_info.get("tankInformation"),
                    "equipment": delivery_info.get("equipment", []),
                    "alertMessage": delivery_info.get("alertMessage")
                }
            }
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


