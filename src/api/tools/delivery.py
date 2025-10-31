from fastapi import APIRouter, Depends, HTTPException

from src.core.deps import get_fontis_client
from src.core.security import verify_api_key
from src.schemas.tools import (
    NextDeliveryTool,
    DeliveryStopsTool,
    DefaultProductsTool,
    NextScheduledDeliveryTool,
    OrdersSearchTool
)
from src.services.fontis_client import FontisClient
from src.core.exceptions import FontisAPIError

router = APIRouter(prefix="/tools/delivery", tags=["tools-delivery"])


@router.post("/stops", dependencies=[Depends(verify_api_key)])
async def get_delivery_stops(
    params: DeliveryStopsTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get all delivery stops for a customer.
    
    Tool ID: a8ff151f77354ae30d328f4042b7ab15
    Fontis Endpoint: POST /api/v1/customers/{customerId}/deliveries
    
    Behavior:
    - Returns all delivery locations tied to a customer account
    - Most customers have 1 stop; multiple stops are edge cases
    - deliveryId from this endpoint is required for most other endpoints
    - Includes route info, next delivery date, and financial summary
    
    AI Usage Guidelines:
    - Call this after customer verification to obtain deliveryId
    - For single stop: Proceed directly with that deliveryId
    - For multiple stops: Ask customer to specify which location
    """
    try:
        response = await fontis.get_delivery_stops(
            customer_id=params.customer_id,
            offset=params.offset,
            take=params.take
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve delivery stops")
            }
        
        data = response.get("data", {})
        stops = data.get("deliveryStops", [])
        summary = data.get("summary", {})
        
        return {
            "success": True,
            "message": f"Found {summary.get('totalDeliveryStops', 0)} delivery stop(s)",
            "data": {
                "stops": stops,
                "summary": {
                    "totalStops": summary.get("totalDeliveryStops"),
                    "totalDue": summary.get("totalDue"),
                    "hasScheduledDeliveries": summary.get("hasScheduledDeliveries"),
                    "routes": summary.get("routes", [])
                }
            }
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/next-scheduled", dependencies=[Depends(verify_api_key)])
async def get_next_scheduled_delivery(
    params: NextScheduledDeliveryTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get the next scheduled delivery for a customer.
    
    Tool ID: 92e47d19800cfe7724e27d11b0ec4f1a
    Fontis Endpoint: POST /api/v1/deliveries/next
    Method: GetDeliveryDays
    
    Purpose:
    Retrieve the next upcoming scheduled route delivery for a specific customer
    delivery stop. Provides fast way to confirm customer's next regular delivery
    date, route day, and route code.
    
    Behavior:
    - Returns single object containing next scheduled route delivery
    - Includes date (ISO 8601), formatted date, dayOfWeek, deliveryRoute
    - Shows ticketNumber and calendarType
    - Searches ahead based on daysAhead parameter (default: 45, max: 90)
    
    Fontis Route Model:
    - 20-business-day delivery rotation (~every 4 weeks, ~13 times/year)
    - Routes grouped geographically with neighbors/businesses
    - Route weekday shifts slightly for holidays or adjustments
    - Regular route deliveries: $3.30 delivery fee
    - Off-route service deliveries: $25 convenience fee, 3-item minimum
    
    AI Usage Guidelines:
    - Use when customer asks "when is my next delivery?"
    - Explain 20-business-day rotation naturally
    - If no delivery found, check if customer is will-call or inactive
    - Communicate route holiday shifts naturally
    - For earlier delivery needs, mention off-route options
    
    Notes:
    - Will-call customers return no delivery until order is scheduled
    - Does NOT include off-route deliveries or online orders
    - Dates may shift slightly for route holidays
    """
    try:
        response = await fontis.get_next_scheduled_delivery(
            customer_id=params.customer_id,
            delivery_id=params.delivery_id,
            days_ahead=params.days_ahead
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "No upcoming deliveries scheduled")
            }
        
        return response
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/default-products", dependencies=[Depends(verify_api_key)])
async def get_default_products(
    params: DefaultProductsTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get default products for a delivery stop (standing order).
    
    Tool ID: f24e6d2bc336153c076f0220b45f86b6
    Fontis Endpoint: POST /api/v1/deliveries/{deliveryId}/defaults
    Method: GetDefaultProducts
    
    Purpose:
    Retrieve standing order default products (what products and quantities
    are automatically delivered each time for a specific delivery stop).
    
    Behavior:
    - Returns list of default products with quantities
    - Includes metadata (totalProducts, activeProducts)
    - quantity = 0: SWAP model (exchange empties for full bottles)
    - quantity > 0: STANDING ORDER (fixed amount each delivery)
    
    AI Usage Guidelines:
    - Use to explain or adjust default deliveries
    - Clearly distinguish between swap and standing order models
    - Explain that swap customers get what they put out
    - Standing order customers get fixed quantities
    """
    try:
        response = await fontis.get_default_products(
            customer_id=params.customer_id,
            delivery_id=params.delivery_id
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve default products")
            }
        
        # Determine delivery model based on quantities
        products = response.get("data", [])
        delivery_type = "swap" if all(p.get("quantity", 0) == 0 for p in products) else "standing_order"
        
        return {
            "success": True,
            "message": f"Customer is on {delivery_type} model",
            "data": response.get("data", []),
            "meta": {
                **response.get("meta", {}),
                "deliveryType": delivery_type
            }
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/search", dependencies=[Depends(verify_api_key)])
async def search_orders(
    params: OrdersSearchTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Search for orders by various criteria.
    
    Fontis Endpoint: POST /api/v1/orders/search
    
    Purpose:
    Search for delivery orders using ticket number, customer ID, delivery ID,
    or combination of filters. Returns orders matching the search criteria.
    
    Behavior:
    - Flexible search with multiple optional parameters
    - Can filter by open/closed orders
    - Can filter to web-orderable products only
    - Returns empty list if no matches found
    
    Search Parameters (at least one should be provided):
    - ticketNumber: Specific order ticket number
    - customerId: All orders for a customer
    - deliveryId: All orders for a delivery stop
    - onlyOpenOrders: Filter to unposted orders only (default: true)
    - webProductsOnly: Filter to web products only (default: false)
    
    AI Usage Guidelines:
    - Use when customer asks "Where's my order #12345?"
    - Use to find pending/open orders for a customer
    - Use to verify order status or details
    - Explain onlyOpenOrders means "not yet completed/posted"
    
    Notes:
    - Returns comprehensive order details including products
    - Empty response doesn't mean error - just no matching orders
    - Use in combination with other order endpoints for full details
    """
    try:
        # Validate at least one search parameter is provided
        if not any([params.ticket_number, params.customer_id, params.delivery_id]):
            return {
                "success": False,
                "message": "At least one search parameter (ticket_number, customer_id, or delivery_id) is required"
            }
        
        response = await fontis.search_orders(
            ticket_number=params.ticket_number,
            customer_id=params.customer_id,
            delivery_id=params.delivery_id,
            only_open_orders=params.only_open_orders,
            web_products_only=params.web_products_only
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to search orders")
            }
        
        return response
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))
