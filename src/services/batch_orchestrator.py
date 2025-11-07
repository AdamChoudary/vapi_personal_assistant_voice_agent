"""
Batch processing orchestrator for declined payment outreach.

Coordinates:
- CSV processing
- Customer matching
- Priority calculation
- Day 0 SMS
- Daily priority-based outreach (calls, SMS, email)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import structlog

from src.services.declined_payment_processor import DeclinedPaymentProcessor
from src.services.priority_calculator import PriorityCalculator, OutreachPriority
from src.services.fontis_client import FontisClient
from src.services.outbound_call_service import get_outbound_service
from src.services.batch_database import BatchDatabase

logger = structlog.get_logger(__name__)


class BatchOrchestrator:
    """Orchestrate declined payment batch processing and outreach."""
    
    def __init__(self, fontis_client: FontisClient, db_path: Optional[Path] = None):
        self.fontis = fontis_client
        self.processor = DeclinedPaymentProcessor(fontis_client)
        self.priority_calc = PriorityCalculator(fontis_client)
        self.outbound_service = get_outbound_service()
        self.db = BatchDatabase(db_path or Path("data/batch_tracking.db"))
    
    async def process_batch_csv(
        self,
        csv_path: Path,
        batch_id: str
    ) -> Dict[str, Any]:
        """
        Process a batch CSV file and initiate Day 0 outreach.
        
        Args:
            csv_path: Path to CSV file
            batch_id: Batch identifier
        
        Returns:
            Processing results with matched customers and SMS status
        """
        logger.info("processing_batch_csv", batch_id=batch_id)
        
        # Process CSV and send Day 0 SMS
        result = await self.processor.process_csv_file(csv_path, batch_id)
        
        # Record batch in database
        self.db.record_batch_processed(
            batch_id=batch_id,
            total_records=result["total_records"],
            declined_count=result["declined_count"],
            matched_count=result["matched_count"],
            sms_sent=result.get("sms_sent", 0),
            csv_filename=csv_path.name
        )
        
        # Record customer declines in database
        matched_customers = result.get("matched_customers", [])
        for customer in matched_customers:
            # Check if repeat decline
            is_repeat = self.db.is_repeat_decline(customer["customer_id"], batch_id)
            priority = "high" if is_repeat else "medium"  # Initial priority
            
            self.db.record_customer_decline(
                customer_id=customer["customer_id"],
                batch_id=batch_id,
                declined_amount=customer["declined_amount"],
                priority=priority
            )
        
        return {
            **result,
            "next_steps": {
                "high_priority_count": 0,  # Will be calculated daily
                "medium_priority_count": 0,
                "low_priority_count": 0,
                "message": "Day 0 SMS sent. Priority-based outreach will begin Day 1+"
            }
        }
    
    async def process_daily_outreach(
        self,
        batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process daily priority-based outreach.
        
        Should be called daily to:
        1. Recalculate priorities for all active declined payment customers
        2. Trigger appropriate outreach based on priority
        3. Skip customers who have already paid
        
        Args:
            batch_id: Optional batch ID to process specific batch only
        
        Returns:
            Daily outreach summary
        """
        logger.info("processing_daily_outreach", batch_id=batch_id)
        
        # Get active declined customers from database
        active_customers = self.db.get_active_declined_customers(batch_id=batch_id)
        
        results = {
            "date": datetime.now().isoformat(),
            "high_priority": {
                "calls_initiated": 0,
                "calls_failed": 0,
                "skipped_paid": 0
            },
            "medium_priority": {
                "sms_sent": 0,
                "sms_failed": 0,
                "skipped_paid": 0
            },
            "low_priority": {
                "email_sent": 0,
                "skipped_paid": 0
            },
            "total_processed": 0
        }
        
        for customer_record in active_customers:
            customer_id = customer_record["customer_id"]
            batch_id_record = customer_record["batch_id"]
            declined_amount = customer_record["declined_amount"]
            is_repeat = customer_record["repeat_decline_count"] > 0
            
            # Get customer details for outreach
            try:
                customer_details = await self.fontis.get_customer_details(customer_id)
                if not customer_details.get("success"):
                    continue
                
                customer_data = customer_details.get("data", {})
                customer_name = customer_data.get("name", "Customer")
                customer_phone = customer_data.get("contact", {}).get("phoneNumber")
                
                if not customer_phone:
                    continue
                
                # Get delivery ID
                delivery_id = await self.priority_calc._get_primary_delivery_id(customer_id)
                
                # Process outreach
                outreach_result = await self.process_customer_outreach(
                    customer_id=customer_id,
                    delivery_id=delivery_id,
                    declined_amount=declined_amount,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    is_repeat_decline=is_repeat,
                    batch_id=batch_id_record
                )
                
                # Record outreach in database
                if outreach_result.get("action") == "call_initiated":
                    self.db.record_outreach(
                        customer_id=customer_id,
                        batch_id=batch_id_record,
                        outreach_type="call",
                        priority=outreach_result.get("priority", "high"),
                        call_id=outreach_result.get("call_id"),
                        success=True
                    )
                    results["high_priority"]["calls_initiated"] += 1
                elif outreach_result.get("action") == "call_failed":
                    self.db.record_outreach(
                        customer_id=customer_id,
                        batch_id=batch_id_record,
                        outreach_type="call",
                        priority="high",
                        success=False,
                        error_message=outreach_result.get("error")
                    )
                    results["high_priority"]["calls_failed"] += 1
                elif outreach_result.get("action") == "sms_sent":
                    self.db.record_outreach(
                        customer_id=customer_id,
                        batch_id=batch_id_record,
                        outreach_type="sms",
                        priority=outreach_result.get("priority", "medium"),
                        sms_id=outreach_result.get("sms_id"),
                        success=True
                    )
                    results["medium_priority"]["sms_sent"] += 1
                elif outreach_result.get("action") == "sms_failed":
                    self.db.record_outreach(
                        customer_id=customer_id,
                        batch_id=batch_id_record,
                        outreach_type="sms",
                        priority="medium",
                        success=False,
                        error_message=outreach_result.get("error")
                    )
                    results["medium_priority"]["sms_failed"] += 1
                elif outreach_result.get("action") == "skipped":
                    if outreach_result.get("reason") == "payment_already_received":
                        results["high_priority"]["skipped_paid"] += 1
                        results["medium_priority"]["skipped_paid"] += 1
                        results["low_priority"]["skipped_paid"] += 1
                
                results["total_processed"] += 1
                
            except Exception as e:
                logger.error("customer_outreach_error", customer_id=customer_id, error=str(e))
                continue
        
        return results
    
    async def process_customer_outreach(
        self,
        customer_id: str,
        delivery_id: Optional[str],
        declined_amount: float,
        customer_name: str,
        customer_phone: str,
        is_repeat_decline: bool = False
    ) -> Dict[str, Any]:
        """
        Process outreach for a single customer based on current priority.
        
        Args:
            customer_id: Fontis customer ID
            delivery_id: Delivery ID
            declined_amount: Amount that was declined
            customer_name: Customer name
            customer_phone: Customer phone number
            is_repeat_decline: True if repeat decline
        
        Returns:
            Outreach result
        """
        # Calculate priority
        priority_result = await self.priority_calc.calculate_priority(
            customer_id=customer_id,
            delivery_id=delivery_id,
            is_repeat_decline=is_repeat_decline
        )
        
        # Skip if already paid
        if not priority_result.payment_still_due:
            if batch_id:
                self.db.mark_customer_resolved(customer_id, batch_id)
            return {
                "customer_id": customer_id,
                "action": "skipped",
                "reason": "payment_already_received",
                "priority": priority_result.priority.value
            }
        
        # Skip if account inactive
        if not priority_result.account_active:
            return {
                "customer_id": customer_id,
                "action": "skipped",
                "reason": "account_inactive",
                "priority": priority_result.priority.value
            }
        
        # Update priority in database if changed
        if batch_id:
            current_records = self.db.get_active_declined_customers(batch_id=batch_id)
            for record in current_records:
                if record["customer_id"] == customer_id:
                    if record["current_priority"] != priority_result.priority.value:
                        # Priority changed - will be updated in record_outreach
                        pass
                    break
        
        # Execute outreach based on priority
        if priority_result.should_call():
            return await self._initiate_call(
                customer_id=customer_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                declined_amount=declined_amount,
                total_due=priority_result.total_due,
                days_until_delivery=priority_result.days_until_delivery
            )
        elif priority_result.should_sms():
            return await self._send_followup_sms(
                customer_id=customer_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                declined_amount=declined_amount,
                total_due=priority_result.total_due,
                days_until_delivery=priority_result.days_until_delivery
            )
        else:
            return {
                "customer_id": customer_id,
                "action": "email_queued",
                "priority": priority_result.priority.value,
                "message": "Email will be sent via email service"
            }
    
    async def _initiate_call(
        self,
        customer_id: str,
        customer_name: str,
        customer_phone: str,
        declined_amount: float,
        total_due: float,
        days_until_delivery: Optional[int]
    ) -> Dict[str, Any]:
        """Initiate AI call for high-priority customer."""
        try:
            message_context = f"Delivery in {days_until_delivery} days" if days_until_delivery else "No delivery scheduled"
            
            customer_data = {
                "customer_id": customer_id,
                "name": customer_name,
                "declined_amount": declined_amount,
                "account_balance": total_due,
                "days_until_delivery": days_until_delivery
            }
            
            call_result = await self.outbound_service.initiate_call(
                customer_phone=customer_phone,
                call_type="declined_payment",
                customer_data=customer_data
            )
            
            # Record outreach
            self.db.record_outreach(
                customer_id=customer_id,
                batch_id=batch_id or "unknown",
                outreach_type="call",
                priority="high",
                call_id=call_result.get("id"),
                success=True
            )
            
            return {
                "customer_id": customer_id,
                "action": "call_initiated",
                "call_id": call_result.get("id"),
                "status": call_result.get("status"),
                "priority": "high"
            }
        except Exception as e:
            logger.error("call_initiation_failed", customer_id=customer_id, error=str(e))
            return {
                "customer_id": customer_id,
                "action": "call_failed",
                "error": str(e),
                "priority": "high"
            }
    
    async def _send_followup_sms(
        self,
        customer_id: str,
        customer_name: str,
        customer_phone: str,
        declined_amount: float,
        total_due: float,
        days_until_delivery: Optional[int]
    ) -> Dict[str, Any]:
        """Send follow-up SMS for medium-priority customer."""
        try:
            if days_until_delivery and days_until_delivery <= 7:
                urgency = f"Your next delivery is in {days_until_delivery} days"
            else:
                urgency = "Your account has an outstanding balance"
            
            message = (
                f"Hi {customer_name}, this is Fontis Water. {urgency}. "
                f"We had an issue processing a payment of ${declined_amount:.2f}. "
                f"Your current balance is ${total_due:.2f}. "
                f"Please update your payment method at fontisweb.com or call us at "
                f"(678) 303-4022 to avoid service interruption."
            )
            
            sms_result = await self.outbound_service.send_sms(
                customer_phone=customer_phone,
                message=message,
                customer_data={
                    "customer_id": customer_id,
                    "declined_amount": declined_amount,
                    "total_due": total_due
                }
            )
            
            # Record outreach
            self.db.record_outreach(
                customer_id=customer_id,
                batch_id=batch_id or "unknown",
                outreach_type="sms",
                priority="medium",
                sms_id=sms_result.get("id"),
                success=True
            )
            
            return {
                "customer_id": customer_id,
                "action": "sms_sent",
                "sms_id": sms_result.get("id"),
                "priority": "medium"
            }
        except Exception as e:
            logger.error("sms_send_failed", customer_id=customer_id, error=str(e))
            return {
                "customer_id": customer_id,
                "action": "sms_failed",
                "error": str(e),
                "priority": "medium"
            }

