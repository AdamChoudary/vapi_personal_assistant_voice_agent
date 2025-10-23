from fastapi import APIRouter, Depends, HTTPException

from src.core.deps import get_fontis_client
from src.core.security import verify_api_key
from src.schemas.tools import CustomerSearchTool, CustomerDetailsTool, FinanceDeliveryInfoTool
from src.services.fontis_client import FontisClient
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
                "success": False,
                "message": "No customers found matching your search.",
                "data": [],
                "meta": {
                    "total": 0,
                    "hasMore": False
                }
            }
        
        # Format results for AI consumption
        formatted_results = []
        for customer in customers:
            formatted_results.append({
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
            })
        
        return {
            "success": True,
            "message": f"Found {pagination.get('total', len(customers))} customer(s)",
            "data": formatted_results,
            "meta": {
                "total": pagination.get("total"),
                "hasMore": pagination.get("hasMore"),
                "returned": len(formatted_results)
            }
        }
        
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
        response = await fontis.get_customer_finance_info(
            customer_id=params.customer_id,
            delivery_id=params.delivery_id
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
