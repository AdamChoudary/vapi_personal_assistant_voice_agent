"""
Priority calculation service for declined payment outreach.

Calculates customer priority based on:
- Next delivery date (0-3 days = High, 4-7 days = Medium, >7 days = Low)
- Repeat declines (always High priority)
- Balance status

Priority determines outreach method:
- High Priority → AI calls (Day 1+)
- Medium Priority → SMS/Email follow-ups
- Low Priority → Email only
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum
import structlog

from src.services.fontis_client import FontisClient
from src.core.exceptions import FontisAPIError

logger = structlog.get_logger(__name__)


class OutreachPriority(str, Enum):
    """Outreach priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PriorityCalculationResult:
    """Result of priority calculation."""
    
    def __init__(
        self,
        priority: OutreachPriority,
        next_delivery_date: Optional[datetime] = None,
        days_until_delivery: Optional[int] = None,
        is_repeat_decline: bool = False,
        account_active: bool = True,
        payment_still_due: bool = True,
        total_due: Optional[float] = None
    ):
        self.priority = priority
        self.next_delivery_date = next_delivery_date
        self.days_until_delivery = days_until_delivery
        self.is_repeat_decline = is_repeat_decline
        self.account_active = account_active
        self.payment_still_due = payment_still_due
        self.total_due = total_due
    
    def should_call(self) -> bool:
        """Determine if customer should receive AI call."""
        return (
            self.priority == OutreachPriority.HIGH
            and self.account_active
            and self.payment_still_due
        )
    
    def should_sms(self) -> bool:
        """Determine if customer should receive SMS."""
        return (
            self.priority in [OutreachPriority.HIGH, OutreachPriority.MEDIUM]
            and self.account_active
            and self.payment_still_due
        )
    
    def should_email(self) -> bool:
        """Determine if customer should receive email."""
        return (
            self.account_active
            and self.payment_still_due
        )


class PriorityCalculator:
    """Calculate outreach priority for declined payment customers."""
    
    def __init__(self, fontis_client: FontisClient):
        self.fontis = fontis_client
    
    async def calculate_priority(
        self,
        customer_id: str,
        delivery_id: Optional[str] = None,
        is_repeat_decline: bool = False
    ) -> PriorityCalculationResult:
        """
        Calculate outreach priority for a customer.
        
        Args:
            customer_id: Fontis customer ID
            delivery_id: Optional delivery ID (will fetch if not provided)
            is_repeat_decline: True if customer has declined before
        
        Returns:
            PriorityCalculationResult with priority and delivery info
        """
        # Pre-call validation
        account_status = await self._check_account_status(customer_id)
        if not account_status["active"]:
            return PriorityCalculationResult(
                priority=OutreachPriority.LOW,
                account_active=False,
                payment_still_due=account_status["payment_due"],
                total_due=account_status["total_due"]
            )
        
        # Check if payment still due
        if not account_status["payment_due"]:
            return PriorityCalculationResult(
                priority=OutreachPriority.LOW,
                account_active=True,
                payment_still_due=False,
                total_due=account_status["total_due"]
            )
        
        # Get delivery ID if not provided
        if not delivery_id:
            delivery_id = await self._get_primary_delivery_id(customer_id)
        
        if not delivery_id:
            # No delivery scheduled - Low priority
            return PriorityCalculationResult(
                priority=OutreachPriority.LOW,
                account_active=True,
                payment_still_due=True,
                total_due=account_status["total_due"]
            )
        
        # Get next delivery date
        delivery_info = await self._get_next_delivery(customer_id, delivery_id)
        
        if not delivery_info["has_delivery"]:
            return PriorityCalculationResult(
                priority=OutreachPriority.LOW,
                account_active=True,
                payment_still_due=True,
                total_due=account_status["total_due"]
            )
        
        next_delivery = delivery_info["delivery_date"]
        days_until = delivery_info["days_until"]
        
        # Calculate priority
        if is_repeat_decline:
            priority = OutreachPriority.HIGH
        elif days_until is not None:
            if days_until <= 3:
                priority = OutreachPriority.HIGH
            elif days_until <= 7:
                priority = OutreachPriority.MEDIUM
            else:
                priority = OutreachPriority.LOW
        else:
            priority = OutreachPriority.LOW
        
        return PriorityCalculationResult(
            priority=priority,
            next_delivery_date=next_delivery,
            days_until_delivery=days_until,
            is_repeat_decline=is_repeat_decline,
            account_active=True,
            payment_still_due=True,
            total_due=account_status["total_due"]
        )
    
    async def _check_account_status(
        self,
        customer_id: str
    ) -> Dict[str, any]:
        """
        Check account status and payment due status.
        
        Returns:
            {
                "active": bool,
                "payment_due": bool,
                "total_due": float
            }
        """
        try:
            # Get customer details to check if active
            customer_response = await self.fontis.get_customer_details(customer_id)
            if not customer_response.get("success"):
                return {
                    "active": False,
                    "payment_due": False,
                    "total_due": 0.0
                }
            
            customer_data = customer_response.get("data", {})
            
            # Get balance
            balance_response = await self.fontis.get_account_balances(customer_id)
            if not balance_response.get("success"):
                return {
                    "active": True,
                    "payment_due": False,
                    "total_due": 0.0
                }
            
            balance_data = balance_response.get("data", {})
            total_due = float(balance_data.get("totalDueBalance", 0) or 0)
            
            return {
                "active": True,
                "payment_due": total_due > 0.01,  # Consider > $0.01 as payment due
                "total_due": total_due
            }
        except Exception as e:
            logger.error("account_status_check_error", customer_id=customer_id, error=str(e))
            return {
                "active": False,
                "payment_due": False,
                "total_due": 0.0
            }
    
    async def _get_primary_delivery_id(self, customer_id: str) -> Optional[str]:
        """Get primary delivery ID for customer."""
        try:
            response = await self.fontis.get_delivery_stops(customer_id, take=1)
            if not response.get("success"):
                return None
            
            stops = response.get("data", {}).get("deliveryStops", [])
            if stops:
                return stops[0].get("deliveryId")
            
            return None
        except Exception as e:
            logger.error("delivery_id_fetch_error", customer_id=customer_id, error=str(e))
            return None
    
    async def _get_next_delivery(
        self,
        customer_id: str,
        delivery_id: str
    ) -> Dict[str, any]:
        """
        Get next scheduled delivery information.
        
        Returns:
            {
                "has_delivery": bool,
                "delivery_date": Optional[datetime],
                "days_until": Optional[int]
            }
        """
        try:
            response = await self.fontis.get_next_scheduled_delivery(
                customer_id=customer_id,
                delivery_id=delivery_id,
                days_ahead=45
            )
            
            if not response.get("success"):
                return {
                    "has_delivery": False,
                    "delivery_date": None,
                    "days_until": None
                }
            
            data = response.get("data", {})
            delivery_date_str = data.get("deliveryDate")
            
            if not delivery_date_str:
                return {
                    "has_delivery": False,
                    "delivery_date": None,
                    "days_until": None
                }
            
            # Parse delivery date
            try:
                # Handle various date formats
                if 'T' in delivery_date_str:
                    delivery_date = datetime.fromisoformat(delivery_date_str.replace('Z', '+00:00'))
                else:
                    delivery_date = datetime.strptime(delivery_date_str, "%Y-%m-%d")
                
                # Calculate business days until delivery
                days_until = self._business_days_until(delivery_date)
                
                return {
                    "has_delivery": True,
                    "delivery_date": delivery_date,
                    "days_until": days_until
                }
            except ValueError as e:
                logger.error("date_parse_error", date_str=delivery_date_str, error=str(e))
                return {
                    "has_delivery": False,
                    "delivery_date": None,
                    "days_until": None
                }
        except Exception as e:
            logger.error("next_delivery_fetch_error", customer_id=customer_id, error=str(e))
            return {
                "has_delivery": False,
                "delivery_date": None,
                "days_until": None
            }
    
    def _business_days_until(self, target_date: datetime) -> int:
        """
        Calculate business days until target date.
        
        Excludes weekends (Saturday=5, Sunday=6).
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        target = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if target <= today:
            return 0
        
        business_days = 0
        current = today
        
        while current < target:
            # Monday=0, Sunday=6
            if current.weekday() < 5:  # Monday-Friday
                business_days += 1
            current += timedelta(days=1)
        
        return business_days


