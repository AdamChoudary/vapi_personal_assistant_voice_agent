from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.core.deps import get_fontis_client
from src.core.security import verify_api_key
from src.schemas.tools import (
    NextDeliveryTool,
    DeliveryStopsTool,
    DefaultProductsTool,
    NextScheduledDeliveryTool,
    OrdersSearchTool,
    DeliverySummaryTool,
    DeliveryScheduleTool,
    WorkOrderStatusTool,
    PricingBreakdownTool,
    OrderChangeStatusTool,
)
from src.services.fontis_client import FontisClient
from src.core.exceptions import FontisAPIError

router = APIRouter(prefix="/tools/delivery", tags=["tools-delivery"])


async def _resolve_delivery_id(
    fontis: FontisClient,
    customer_id: str,
    delivery_id: str | None,
) -> str | None:
    """Resolve a delivery ID for the customer when not explicitly provided."""
    if delivery_id:
        return delivery_id

    try:
        stops_response = await fontis.get_delivery_stops(customer_id=customer_id, offset=0, take=10)
    except FontisAPIError:
        return None

    if not stops_response.get("success"):
        return None

    data = stops_response.get("data", {})
    stops = data.get("deliveryStops")

    if stops is None:
        if isinstance(data, list):
            stops = data
        elif isinstance(data, dict):
            stops = data.get("stops") or data.get("data")

    if not stops:
        return None

    for stop in stops:
        candidate = stop.get("deliveryId") or stop.get("id")
        if candidate:
            return candidate

    return None


def _coerce_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _is_schedule_completed(entry: dict[str, Any]) -> bool:
    status = (entry.get("status") or "").lower()
    if status in {"completed", "complete", "delivered", "posted"}:
        return True
    if entry.get("invoicePosted") or entry.get("deliveryCompleted"):
        return True
    invoice_total = entry.get("invoiceTotal")
    if isinstance(invoice_total, (int, float)) and invoice_total > 0:
        return True
    return False


def _is_schedule_skipped(entry: dict[str, Any]) -> bool:
    status = (entry.get("status") or "").lower()
    if status in {"skipped", "skip"}:
        return True
    if entry.get("skipReason"):
        return True
    if entry.get("skipped") is True:
        return True
    return False


def _order_is_open(order: dict[str, Any]) -> bool:
    status = (order.get("status") or "").lower()
    if status in {"completed", "complete", "closed", "cancelled", "canceled"}:
        return False
    if order.get("posted") is True or order.get("isClosed") is True:
        return False
    if status in {"open", "pending", "scheduled", "in progress"}:
        return True
    if order.get("posted") is False or order.get("isClosed") is False:
        return True
    if order.get("invoiceTotal") in (None, 0) and order.get("completed") is not True:
        return True
    return False


def _safe_decimal(value: Any) -> float | None:
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


@router.post("/summary", dependencies=[Depends(verify_api_key)])
async def get_delivery_summary(
    params: DeliverySummaryTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Aggregate delivery, financial, and equipment context for a customer stop.
    
    Tool ID: (aggregated endpoint - combines multiple Fontis API calls)
    Fontis Endpoints: Combines finance-info, next-scheduled-delivery, default-products
    
    Purpose:
    Provides comprehensive delivery context including route, driver, equipment,
    next delivery date, and standing order defaults in a single response.
    """
    delivery_id = await _resolve_delivery_id(fontis, params.customer_id, params.delivery_id)
    if not delivery_id:
        return {
            "success": False,
            "message": "Unable to resolve delivery ID for this customer. Verify the account has an active delivery location.",
        }

    try:
        finance_response = await fontis.get_customer_finance_info(
            customer_id=params.customer_id,
            delivery_id=delivery_id,
        )
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not finance_response.get("success"):
        return {
            "success": False,
            "message": finance_response.get("message", "Failed to retrieve finance/delivery snapshot"),
        }

    data = finance_response.get("data", {})
    customer_info = data.get("customerInfo", {})
    delivery_info = data.get("deliveryInfo", {})

    driver_name = (
        delivery_info.get("routeDriver")
        or delivery_info.get("driverName")
        or delivery_info.get("driver")
    )
    driver_contact = delivery_info.get("driverPhone") or delivery_info.get("driverContact")

    next_delivery_source = "deliveryInfo"
    next_delivery = None
    if params.include_next_delivery:
        try:
            next_response = await fontis.get_next_scheduled_delivery(
                customer_id=params.customer_id,
                delivery_id=delivery_id,
                days_ahead=45,
            )
            if next_response.get("success"):
                next_delivery = next_response.get("data")
                next_delivery_source = "nextScheduledDelivery"
        except FontisAPIError:
            next_delivery = None

    if next_delivery is None:
        next_delivery = {
            "deliveryDate": delivery_info.get("nextDeliveryDate"),
            "routeDay": delivery_info.get("routeDay"),
            "routeCode": delivery_info.get("routeCode"),
        } if delivery_info.get("nextDeliveryDate") else None

    defaults = []
    defaults_meta: dict[str, Any] = {}
    if params.include_defaults:
        try:
            defaults_response = await fontis.get_default_products(
                customer_id=params.customer_id,
                delivery_id=delivery_id,
            )
            if defaults_response.get("success"):
                defaults = defaults_response.get("data", [])
                defaults_meta = defaults_response.get("meta", {})
        except FontisAPIError:
            defaults = []

    standing_order_items = []
    for item in defaults:
        standing_order_items.append({
            "code": item.get("productCode") or item.get("code"),
            "description": item.get("productDescription") or item.get("description"),
            "quantity": item.get("quantity"),
            "unitPrice": (
                _safe_decimal(item.get("unitPrice"))
                or _safe_decimal(item.get("price"))
                or _safe_decimal(item.get("defaultPrice"))
            ),
            "deliveryMode": item.get("deliveryMode") or item.get("defaultType"),
        })

    alerts = [alert for alert in [
        delivery_info.get("alertMessage"),
        delivery_info.get("serviceAlert"),
        delivery_info.get("deliveryAlert"),
    ] if alert]

    return {
        "success": True,
        "message": "Delivery summary retrieved successfully",
        "data": {
            "customerId": params.customer_id,
            "deliveryId": delivery_id,
            "route": {
                "code": delivery_info.get("routeCode"),
                "day": delivery_info.get("routeDay"),
                "schedulingArea": delivery_info.get("schedulingArea"),
            },
            "driver": {
                "name": driver_name,
                "contact": driver_contact,
                "csr": delivery_info.get("csr") or delivery_info.get("customerServiceRep"),
            },
            "nextDelivery": next_delivery,
            "equipment": delivery_info.get("equipment", []),
            "alerts": alerts,
            "financial": {
                "currentBalance": customer_info.get("currentBalance"),
                "formattedBalance": customer_info.get("formattedCurrentBalance"),
                "pastDue": customer_info.get("pastDue"),
                "formattedPastDue": customer_info.get("formattedPastDue"),
                "hasPastDue": customer_info.get("hasPastDue"),
                "lastPayment": customer_info.get("lastPayment"),
            },
            "standingOrder": {
                "items": standing_order_items,
                "meta": defaults_meta,
            } if standing_order_items else None,
        },
        "meta": {
            "nextDeliverySource": next_delivery_source,
        },
    }


@router.post("/schedule", dependencies=[Depends(verify_api_key)])
async def get_delivery_schedule(
    params: DeliveryScheduleTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Retrieve scheduled deliveries for a customer within a date range.
    
    Tool ID: 248fa66e8012d7f62a7ca15199a7e67e
    Fontis Endpoint: POST /api/v1/customers/deliveryschedule
    Method: GetDeliveryDays
    
    Purpose:
    Retrieve upcoming and past scheduled deliveries for a customer over a date range.
    Shows regular route deliveries only, not off-route.
    """
    delivery_id = await _resolve_delivery_id(fontis, params.customer_id, params.delivery_id)
    if not delivery_id:
        return {
            "success": False,
            "message": "Unable to resolve delivery ID for this customer.",
        }

    today = date.today()
    start_date = params.from_date or (today - timedelta(days=params.history_days)).isoformat()
    end_date = params.to_date or (today + timedelta(days=params.future_days)).isoformat()

    try:
        schedule_entries = await fontis.get_delivery_schedule(
            customer_id=params.customer_id,
            delivery_id=delivery_id,
            from_date=start_date,
            to_date=end_date,
        )
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

    completed = [_entry for _entry in schedule_entries if _is_schedule_completed(_entry)]
    skipped = [_entry for _entry in schedule_entries if _is_schedule_skipped(_entry)]

    upcoming_entries = []
    for entry in schedule_entries:
        delivery_date = _coerce_date(entry.get("deliveryDate"))
        if delivery_date and delivery_date.date() >= today:
            upcoming_entries.append(entry)

    return {
        "success": True,
        "message": f"Found {len(schedule_entries)} scheduled deliveries between {start_date} and {end_date}",
        "data": schedule_entries,
        "summary": {
            "total": len(schedule_entries),
            "completed": len(completed),
            "skipped": len(skipped),
            "upcoming": len(upcoming_entries),
            "range": {
                "from": start_date,
                "to": end_date,
            },
        },
    }


@router.post("/work-orders", dependencies=[Depends(verify_api_key)])
async def get_work_order_status(
    params: WorkOrderStatusTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Retrieve recent off-route orders or work orders for a delivery stop.
    
    Tool ID: b4e4f83221662ac8d966ec9e5cc6cfb2
    Fontis Endpoint: POST /api/v1/customers/lastdeliveryorders
    Method: GetDeliveryOrders
    
    Purpose:
    Retrieve off-route deliveries and customer-placed online orders.
    These are service tickets, not regular route deliveries.
    Does NOT reflect complete delivery history - only off-route orders.
    """
    delivery_id = await _resolve_delivery_id(fontis, params.customer_id, params.delivery_id)
    if not delivery_id:
        return {
            "success": False,
            "message": "Unable to resolve delivery ID for this customer.",
        }

    try:
        orders_response = await fontis.get_last_delivery_orders(
            customer_id=params.customer_id,
            delivery_id=delivery_id,
            number_of_orders=params.limit,
        )
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not orders_response.get("success"):
        return {
            "success": False,
            "message": orders_response.get("message", "Failed to retrieve work orders"),
        }

    orders = orders_response.get("data", [])
    open_orders = [order for order in orders if _order_is_open(order)]

    return {
        "success": True,
        "message": f"Found {len(orders)} recent work orders/off-route deliveries",
        "data": orders,
        "summary": {
            "total": len(orders),
            "open": len(open_orders),
            "closed": len(orders) - len(open_orders),
        },
    }


@router.post("/pricing-breakdown", dependencies=[Depends(verify_api_key)])
async def get_pricing_breakdown(
    params: PricingBreakdownTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Provide pricing context for the customer's standing order and catalog.
    
    Tool ID: (aggregated endpoint - combines default-products and products catalog)
    Fontis Endpoints: Combines default-products and products catalog calls
    
    Purpose:
    Provides pricing breakdown for standing order and optional catalog excerpt.
    """
    delivery_id = await _resolve_delivery_id(fontis, params.customer_id, params.delivery_id)
    if not delivery_id:
        return {
            "success": False,
            "message": "Unable to resolve delivery ID for this customer.",
        }

    try:
        defaults_response = await fontis.get_default_products(
            customer_id=params.customer_id,
            delivery_id=delivery_id,
        )
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not defaults_response.get("success"):
        return {
            "success": False,
            "message": defaults_response.get("message", "Failed to retrieve standing order defaults"),
        }

    default_items = defaults_response.get("data", [])

    product_catalog = {}
    catalog_excerpt = []
    try:
        products_response = await fontis.get_products(
            customer_id=params.customer_id,
            delivery_id=delivery_id,
            postal_code=params.postal_code,
            internet_only=params.internet_only,
            categories=None,
            default_products=False,
            offset=0,
            take=100,
        )
        if products_response.get("success"):
            records = products_response.get("data", {}).get("records", [])
            product_catalog = {record.get("code"): record for record in records if record.get("code")}
            if params.include_catalog_excerpt:
                catalog_excerpt = [
                    {
                        "code": record.get("code"),
                        "description": record.get("description"),
                        "formattedPrice": record.get("formattedPrice"),
                        "unitDescription": record.get("unitDescription"),
                        "category": record.get("productClass"),
                    }
                    for record in records[:10]
                ]
    except FontisAPIError:
        product_catalog = {}

    standing_order = []
    subtotal = 0.0
    for item in default_items:
        code = item.get("productCode") or item.get("code")
        quantity = _safe_decimal(item.get("quantity")) or 0

        unit_price = (
            _safe_decimal(item.get("unitPrice"))
            or _safe_decimal(item.get("price"))
            or _safe_decimal(item.get("defaultPrice"))
        )
        if unit_price is None and code and code in product_catalog:
            unit_price = _safe_decimal(product_catalog[code].get("defaultPrice"))

        line_total = unit_price * quantity if unit_price is not None else None
        if line_total is not None:
            subtotal += line_total

        standing_order.append({
            "code": code,
            "description": item.get("productDescription") or item.get("description"),
            "quantity": quantity,
            "unitPrice": unit_price,
            "lineTotal": line_total,
            "deliveryMode": item.get("deliveryMode") or item.get("defaultType"),
        })

    summary = {
        "subtotal": subtotal if standing_order else None,
        "items": len(standing_order),
    }

    return {
        "success": True,
        "message": "Pricing breakdown generated successfully",
        "data": {
            "standingOrder": standing_order,
            "catalogExcerpt": catalog_excerpt or None,
        },
        "summary": summary,
    }


@router.post("/order-change-status", dependencies=[Depends(verify_api_key)])
async def get_order_change_status(
    params: OrderChangeStatusTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Confirm whether a pending order/change request exists for the customer.
    
    Tool ID: (aggregated endpoint - uses search_orders with filters)
    Fontis Endpoint: Uses orders/search with onlyOpenOrders filter
    
    Purpose:
    Check for pending order changes or special delivery tickets for the customer.
    """
    delivery_id = await _resolve_delivery_id(fontis, params.customer_id, params.delivery_id)
    if not delivery_id:
        return {
            "success": False,
            "message": "Unable to resolve delivery ID for this customer.",
        }

    try:
        orders_response = await fontis.search_orders(
            ticket_number=params.ticket_number,
            customer_id=params.customer_id,
            delivery_id=delivery_id,
            only_open_orders=params.only_open_orders,
            web_products_only=False,
        )
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not orders_response.get("success"):
        return {
            "success": False,
            "message": orders_response.get("message", "Failed to retrieve order status"),
        }

    orders = orders_response.get("data", [])
    open_orders = [order for order in orders if _order_is_open(order)]

    normalized_orders = []
    for order in orders:
        normalized_orders.append({
            "ticketNumber": order.get("ticketNumber"),
            "status": order.get("status"),
            "scheduledDate": order.get("scheduledDate") or order.get("deliveryDate"),
            "invoiceTotal": order.get("invoiceTotal"),
            "posted": order.get("posted"),
        })

    return {
        "success": True,
        "message": "Open orders found" if open_orders else "No pending orders located",
        "data": normalized_orders,
        "summary": {
            "total": len(orders),
            "open": len(open_orders),
            "ticketQueried": params.ticket_number,
        },
    }
