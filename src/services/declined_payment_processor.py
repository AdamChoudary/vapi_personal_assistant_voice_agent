"""
Automated declined payment processing service.

Handles CSV batch processing, customer matching, priority calculation,
and automated outreach (SMS + calls) for declined credit card payments.

Workflow:
1. Email monitoring → CSV attachment detection
2. CSV parsing → Extract declined transactions
3. Customer matching → phone → email → name+address
4. Balance validation → Confirm match via /balances API
5. Day 0: SMS all customers immediately
6. Daily priority calculation → High/Medium/Low based on delivery date
7. Priority-based outreach → Calls (High), SMS/Email (Medium), Email (Low)
8. Pre-call validation → Check account active, delivery date, payment status
"""

import csv
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import structlog

from src.services.fontis_client import FontisClient
from src.services.outbound_call_service import get_outbound_service
from src.core.exceptions import FontisAPIError

logger = structlog.get_logger(__name__)


class DeclinedPaymentRecord:
    """Parsed declined payment record from CSV."""
    
    def __init__(self, row: Dict[str, str]):
        self.transaction_id = row.get("id", "")
        self.customer_id_csv = row.get("customer_id", "")  # May not be Fontis ID
        self.amount = float(row.get("amount", 0) or 0)
        self.status = row.get("status", "").lower()
        self.response_code = row.get("response_code", "")
        self.processor_response = row.get("processor_response_text", "")
        
        # Customer contact info
        self.billing_first_name = row.get("billing_first_name", "").strip()
        self.billing_last_name = row.get("billing_last_name", "").strip()
        self.billing_phone = self._normalize_phone(row.get("billing_phone", ""))
        self.billing_email = row.get("billing_email", "").strip().lower()
        self.billing_address_line_1 = row.get("billing_address_line_1", "").strip()
        self.billing_city = row.get("billing_city", "").strip()
        self.billing_state = row.get("billing_state", "").strip()
        self.billing_postal_code = row.get("billing_postal_code", "").strip()
        
        self.created_at = row.get("created_at", "")
        self.batch_id = None  # Set during CSV processing
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone to E.164 format."""
        if not phone:
            return ""
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        # Add +1 if 10 digits, assume US
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"
        return phone
    
    @property
    def full_name(self) -> str:
        """Full customer name."""
        return f"{self.billing_first_name} {self.billing_last_name}".strip()
    
    @property
    def full_address(self) -> str:
        """Full address string for matching."""
        parts = [
            self.billing_address_line_1,
            self.billing_city,
            self.billing_state,
            self.billing_postal_code
        ]
        return ", ".join([p for p in parts if p])
    
    def is_declined(self) -> bool:
        """Check if transaction is declined."""
        return self.status == "declined" and self.response_code in ["200", "201", "202", "222", "223"]


class CustomerMatchResult:
    """Result of customer matching process."""
    
    def __init__(
        self,
        matched: bool,
        customer_id: Optional[str] = None,
        delivery_id: Optional[str] = None,
        match_method: Optional[str] = None,
        confidence: str = "low",
        total_due: Optional[float] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None
    ):
        self.matched = matched
        self.customer_id = customer_id
        self.delivery_id = delivery_id
        self.match_method = match_method  # "phone", "email", "name_address"
        self.confidence = confidence  # "high", "medium", "low"
        self.total_due = total_due
        self.customer_name = customer_name
        self.customer_phone = customer_phone


class DeclinedPaymentProcessor:
    """Process declined payment CSV files and trigger automated outreach."""
    
    def __init__(self, fontis_client: FontisClient):
        self.fontis = fontis_client
        self.outbound_service = get_outbound_service()
    
    async def process_csv_file(self, csv_path: Path, batch_id: str) -> Dict[str, Any]:
        """
        Process a declined payment CSV file.
        
        Args:
            csv_path: Path to CSV file
            batch_id: Batch identifier from filename
        
        Returns:
            Processing summary with matched/unmatched counts
        """
        logger.info("processing_declined_payment_csv", batch_id=batch_id, file=str(csv_path))
        
        # Parse CSV
        records = self._parse_csv(csv_path, batch_id)
        declined_records = [r for r in records if r.is_declined()]
        
        logger.info(
            "csv_parsed",
            batch_id=batch_id,
            total_records=len(records),
            declined_count=len(declined_records)
        )
        
        if not declined_records:
            return {
                "success": True,
                "batch_id": batch_id,
                "total_records": len(records),
                "declined_count": 0,
                "matched_count": 0,
                "unmatched_count": 0,
                "message": "No declined payments found in CSV"
            }
        
        # Match customers
        matched_customers = []
        unmatched_records = []
        
        for record in declined_records:
            match_result = await self._match_customer(record)
            if match_result.matched:
                matched_customers.append({
                    "record": record,
                    "match": match_result
                })
            else:
                unmatched_records.append(record)
        
        logger.info(
            "customer_matching_complete",
            batch_id=batch_id,
            matched=len(matched_customers),
            unmatched=len(unmatched_records)
        )
        
        # Day 0: Send SMS to all matched customers
        sms_results = await self._send_day_zero_sms(matched_customers)
        
        return {
            "success": True,
            "batch_id": batch_id,
            "total_records": len(records),
            "declined_count": len(declined_records),
            "matched_count": len(matched_customers),
            "unmatched_count": len(unmatched_records),
            "sms_sent": sms_results["sent"],
            "sms_failed": sms_results["failed"],
            "matched_customers": [
                {
                    "customer_id": m["match"].customer_id,
                    "name": m["match"].customer_name,
                    "phone": m["match"].customer_phone,
                    "declined_amount": m["record"].amount,
                    "total_due": m["match"].total_due,
                    "match_method": m["match"].match_method
                }
                for m in matched_customers
            ],
            "unmatched_records": [
                {
                    "name": r.full_name,
                    "phone": r.billing_phone,
                    "email": r.billing_email,
                    "amount": r.amount
                }
                for r in unmatched_records
            ]
        }
    
    def _parse_csv(self, csv_path: Path, batch_id: str) -> List[DeclinedPaymentRecord]:
        """Parse CSV file and extract declined payment records."""
        records = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = DeclinedPaymentRecord(row)
                record.batch_id = batch_id
                records.append(record)
        
        return records
    
    async def _match_customer(
        self,
        record: DeclinedPaymentRecord
    ) -> CustomerMatchResult:
        """
        Match CSV record to Fontis customer using priority order:
        1. Phone number
        2. Email address
        3. Name + Address
        4. Validate match via balance API
        """
        # Try phone first
        if record.billing_phone:
            match = await self._match_by_phone(record.billing_phone, record.amount)
            if match.matched:
                return match
        
        # Try email
        if record.billing_email:
            match = await self._match_by_email(record.billing_email, record.amount)
            if match.matched:
                return match
        
        # Try name + address
        if record.full_name and record.full_address:
            match = await self._match_by_name_address(
                record.full_name,
                record.full_address,
                record.amount
            )
            if match.matched:
                return match
        
        # No match found
        logger.warning(
            "customer_match_failed",
            name=record.full_name,
            phone=record.billing_phone,
            email=record.billing_email
        )
        return CustomerMatchResult(matched=False)
    
    async def _match_by_phone(
        self,
        phone: str,
        declined_amount: float
    ) -> CustomerMatchResult:
        """Match customer by phone number."""
        try:
            # Search by phone
            response = await self.fontis.search_customers(phone)
            if not response.get("success"):
                return CustomerMatchResult(matched=False)
            
            customers = self._extract_customers(response)
            if not customers:
                return CustomerMatchResult(matched=False)
            
            # Try to match by balance validation
            for customer in customers:
                customer_id = customer.get("customerId")
                if not customer_id:
                    continue
                
                # Validate match via balance API
                balance_match = await self._validate_balance_match(
                    customer_id,
                    declined_amount
                )
                if balance_match:
                    delivery_id = await self._get_primary_delivery_id(customer_id)
                    return CustomerMatchResult(
                        matched=True,
                        customer_id=customer_id,
                        delivery_id=delivery_id,
                        match_method="phone",
                        confidence="high",
                        total_due=balance_match,
                        customer_name=customer.get("name"),
                        customer_phone=phone
                    )
            
            return CustomerMatchResult(matched=False)
        except Exception as e:
            logger.error("phone_match_error", phone=phone, error=str(e))
            return CustomerMatchResult(matched=False)
    
    async def _match_by_email(
        self,
        email: str,
        declined_amount: float
    ) -> CustomerMatchResult:
        """Match customer by email address."""
        try:
            response = await self.fontis.search_customers(email)
            if not response.get("success"):
                return CustomerMatchResult(matched=False)
            
            customers = self._extract_customers(response)
            if not customers:
                return CustomerMatchResult(matched=False)
            
            for customer in customers:
                customer_id = customer.get("customerId")
                if not customer_id:
                    continue
                
                balance_match = await self._validate_balance_match(
                    customer_id,
                    declined_amount
                )
                if balance_match:
                    delivery_id = await self._get_primary_delivery_id(customer_id)
                    return CustomerMatchResult(
                        matched=True,
                        customer_id=customer_id,
                        delivery_id=delivery_id,
                        match_method="email",
                        confidence="high",
                        total_due=balance_match,
                        customer_name=customer.get("name"),
                        customer_phone=customer.get("contact", {}).get("phoneNumber")
                    )
            
            return CustomerMatchResult(matched=False)
        except Exception as e:
            logger.error("email_match_error", email=email, error=str(e))
            return CustomerMatchResult(matched=False)
    
    async def _match_by_name_address(
        self,
        name: str,
        address: str,
        declined_amount: float
    ) -> CustomerMatchResult:
        """Match customer by name and address."""
        try:
            # Try searching by address first (more specific)
            response = await self.fontis.search_customers(address)
            if not response.get("success"):
                return CustomerMatchResult(matched=False)
            
            customers = self._extract_customers(response)
            if not customers:
                return CustomerMatchResult(matched=False)
            
            # Filter by name match
            name_parts = name.lower().split()
            for customer in customers:
                customer_name = customer.get("name", "").lower()
                # Check if name parts match
                if not all(part in customer_name for part in name_parts if len(part) > 2):
                    continue
                
                customer_id = customer.get("customerId")
                if not customer_id:
                    continue
                
                balance_match = await self._validate_balance_match(
                    customer_id,
                    declined_amount
                )
                if balance_match:
                    delivery_id = await self._get_primary_delivery_id(customer_id)
                    return CustomerMatchResult(
                        matched=True,
                        customer_id=customer_id,
                        delivery_id=delivery_id,
                        match_method="name_address",
                        confidence="medium",
                        total_due=balance_match,
                        customer_name=customer.get("name"),
                        customer_phone=customer.get("contact", {}).get("phoneNumber")
                    )
            
            return CustomerMatchResult(matched=False)
        except Exception as e:
            logger.error("name_address_match_error", name=name, address=address, error=str(e))
            return CustomerMatchResult(matched=False)
    
    async def _validate_balance_match(
        self,
        customer_id: str,
        declined_amount: float,
        tolerance: float = 5.0
    ) -> Optional[float]:
        """
        Validate customer match by checking if balance matches declined amount.
        
        Returns total_due if match is valid, None otherwise.
        """
        try:
            response = await self.fontis.get_account_balances(customer_id)
            if not response.get("success"):
                return None
            
            data = response.get("data", {})
            total_due = float(data.get("totalDueBalance", 0) or 0)
            
            # Match if balance is within tolerance of declined amount
            # (account may have accrued additional charges)
            if total_due >= (declined_amount - tolerance):
                return total_due
            
            return None
        except Exception as e:
            logger.error("balance_validation_error", customer_id=customer_id, error=str(e))
            return None
    
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
    
    def _extract_customers(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract customer list from API response."""
        data_field = response.get("data", {})
        if isinstance(data_field, list):
            return data_field
        elif isinstance(data_field, dict):
            return data_field.get("data", [])
        return []
    
    async def _send_day_zero_sms(
        self,
        matched_customers: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Send Day 0 SMS to all matched customers."""
        sent = 0
        failed = 0
        
        for item in matched_customers:
            record = item["record"]
            match = item["match"]
            
            if not match.customer_phone:
                failed += 1
                continue
            
            message = (
                f"Hi {match.customer_name or 'there'}, this is Fontis Water. "
                f"We had an issue processing a payment of ${record.amount:.2f}. "
                f"Your current balance is ${match.total_due:.2f}. "
                f"Please update your payment method at fontisweb.com or call us at "
                f"(678) 303-4022 to avoid service interruption."
            )
            
            try:
                await self.outbound_service.send_sms(
                    customer_phone=match.customer_phone,
                    message=message,
                    customer_data={
                        "customer_id": match.customer_id,
                        "declined_amount": record.amount,
                        "total_due": match.total_due
                    }
                )
                sent += 1
                logger.info(
                    "day_zero_sms_sent",
                    customer_id=match.customer_id,
                    phone=match.customer_phone
                )
            except Exception as e:
                failed += 1
                logger.error(
                    "day_zero_sms_failed",
                    customer_id=match.customer_id,
                    phone=match.customer_phone,
                    error=str(e)
                )
        
        return {"sent": sent, "failed": failed}


