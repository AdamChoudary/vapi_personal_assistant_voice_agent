from fastapi import APIRouter, Depends, HTTPException

from src.core.deps import get_fontis_client
from src.core.security import verify_api_key
from src.schemas.tools import RouteStopsTool
from src.services.fontis_client import FontisClient
from src.core.exceptions import FontisAPIError

router = APIRouter(prefix="/tools/routes", tags=["tools-routes"])


@router.post("/stops", dependencies=[Depends(verify_api_key)])
async def get_route_stops(
    params: RouteStopsTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get all customer stops for a specific route and date.
    
    Tool ID: b02a838764b22f83dce17e848fa63884
    Fontis Endpoint: POST /api/v1/routes/stops
    Method: GetRouteStops
    
    Purpose:
    Retrieve all customer stops for a specific route and date, including
    invoice data and skip reasons. Used internally to confirm route completion
    or investigate skipped deliveries.
    
    Behavior:
    - Returns ALL stops on specified route for specified date
    - Each stop includes delivery status (completed, skipped, pending)
    - Shows invoice totals and skip reasons
    - Can be filtered to specific customer using accountNumber
    
    Response Fields Per Stop:
    - accountNumber, customerName, customerAddress
    - deliveryId, routeCode, scheduleDate
    - invoiceTotal (>0 = completed delivery)
    - skipReason (present = delivery skipped)
    - invoiceKey, ticketNumber (if delivery completed)
    - calendarId, calendarSequence (internal routing)
    - latitude, longitude (GPS coordinates)
    
    Business Logic:
    - invoiceTotal > 0 → delivery completed
    - skipReason present → delivery skipped
    - Most common skip reasons:
      * "No Bottles Out"
      * "Will Call"
      * "Not Needed/Stock OK"
      * "Closed during regular hrs"
      * "Service as Scheduled"
      * "Srvc'd on other Ticket"
    
    AI Usage Guidelines:
    - Use to verify "Why wasn't I serviced on X date?"
    - Explain skip reasons empathetically
    - "No Bottles Out" means no empties were left out for exchange
    - Can confirm other customers on route were serviced
    - Mainly operational/internal - not primary customer-facing endpoint
    
    Notes:
    - Requires exact route code and date
    - Returns complete route manifest for that date
    - Use accountNumber filter to isolate specific customer
    - Some stops may have multiple entries (reschedules, changes)
    - Empty invoiceTotal doesn't always mean skip (could be will-call)
    """
    try:
        response = await fontis.get_route_stops(
            route=params.route,
            route_date=params.route_date,
            account_number=params.account_number
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve route stops")
            }
        
        stops = response.get("data", [])
        
        # Provide summary statistics
        total_stops = len(stops)
        completed = len([s for s in stops if s.get("invoiceTotal", 0) > 0])
        skipped = len([s for s in stops if s.get("skipReason")])
        
        return {
            "success": True,
            "message": f"Found {total_stops} stop(s) on route {params.route} for {params.route_date}",
            "data": stops,
            "summary": {
                "totalStops": total_stops,
                "completed": completed,
                "skipped": skipped,
                "pending": total_stops - completed - skipped
            }
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

