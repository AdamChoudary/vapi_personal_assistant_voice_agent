"""
Admin endpoints for declined payment batch processing.

Endpoints for:
- Manual CSV upload and processing
- Trigger daily outreach processing
- View processing status and results
"""

from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Form
from pydantic import BaseModel
import structlog

from src.services.fontis_client import FontisClient
from src.core.deps import get_fontis_client
from src.core.security import verify_api_key
from src.services.batch_orchestrator import BatchOrchestrator
from src.services.email_monitor import CSVEmailMonitor
from src.services.email_integration import EmailIntegrationService
from src.config import settings
import tempfile

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/batch", tags=["admin", "batch"])


class BatchProcessResponse(BaseModel):
    """Response after processing batch CSV."""
    success: bool
    batch_id: str
    total_records: int
    declined_count: int
    matched_count: int
    unmatched_count: int
    sms_sent: int
    sms_failed: int
    message: str


class DailyOutreachResponse(BaseModel):
    """Response from daily outreach processing."""
    success: bool
    date: str
    high_priority: dict
    medium_priority: dict
    low_priority: dict
    total_processed: int


class EmailCheckResponse(BaseModel):
    """Response from email check operation."""
    success: bool
    emails_checked: int
    csv_files_found: int
    csv_files_processed: int
    batches_processed: List[str]
    errors: List[str]


@router.post("/check-email", response_model=EmailCheckResponse)
async def check_email_for_csvs(
    folder: str = "INBOX",
    days_back: int = 7,
    fontis: FontisClient = Depends(get_fontis_client),
    _: str = Depends(verify_api_key)
):
    """
    Check email inbox for CSV batch files and process them automatically.
    
    This endpoint:
    1. Connects to email server (IMAP)
    2. Searches for emails with CSV attachments matching pattern: Batch_*_result.csv
    3. Downloads CSV files
    4. Automatically processes each CSV (matches customers, sends Day 0 SMS)
    5. Records batches in database
    
    Should be called:
    - Weekly via cron job (to check for monthly CSV)
    - Daily if expecting frequent CSVs
    - Manually when CSV is expected
    
    Args:
        folder: Email folder to check (default: INBOX)
        days_back: Number of days to look back for emails (default: 7)
    """
    logger.info("checking_email_for_csvs", folder=folder, days_back=days_back)
    
    # Check if email configuration is set
    if not settings.email_imap_server or not settings.email_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email monitoring not configured. Set EMAIL_IMAP_SERVER, EMAIL_ADDRESS, and EMAIL_PASSWORD in environment variables."
        )
    
    csv_download_dir = Path(settings.csv_download_dir)
    orchestrator = BatchOrchestrator(fontis)
    
    # Initialize email service
    email_service = EmailIntegrationService(
        imap_server=settings.email_imap_server,
        imap_port=settings.email_imap_port,
        email_address=settings.email_address,
        email_password=settings.email_password,
        download_dir=csv_download_dir
    )
    
    batches_processed = []
    errors = []
    csv_files_found = 0
    csv_files_processed = 0
    
    try:
        # Connect to email
        if not await email_service.connect():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to email server"
            )
        
        # Calculate date to search from
        from datetime import datetime, timedelta
        since_date = datetime.now() - timedelta(days=days_back)
        
        # Check for CSV attachments
        csv_files = await email_service.check_for_new_csvs(
            folder=folder,
            since_date=since_date
        )
        
        csv_files_found = len(csv_files)
        logger.info("csv_files_found", count=csv_files_found)
        
        # Process each CSV file
        for csv_file_info in csv_files:
            batch_id = csv_file_info["batch_id"]
            file_path = csv_file_info["file_path"]
            
            try:
                # Check if batch already processed (via database)
                if orchestrator.db.is_batch_processed(batch_id):
                    logger.info("batch_already_processed", batch_id=batch_id)
                    continue
                
                # Process CSV
                logger.info("processing_csv_from_email", batch_id=batch_id, file_path=str(file_path))
                result = await orchestrator.process_batch_csv(file_path, batch_id)
                
                if result.get("success"):
                    batches_processed.append(batch_id)
                    csv_files_processed += 1
                    
                    # Mark email as read (optional)
                    email_id = csv_file_info.get("email_id")
                    if email_id:
                        await email_service.mark_email_read(email_id, folder)
                    
                    logger.info("csv_processed_successfully", batch_id=batch_id)
                else:
                    errors.append(f"Failed to process batch {batch_id}: {result.get('message', 'Unknown error')}")
            
            except Exception as e:
                error_msg = f"Error processing batch {batch_id}: {str(e)}"
                logger.error("csv_processing_error", batch_id=batch_id, error=str(e), exc_info=True)
                errors.append(error_msg)
        
        # Disconnect from email
        email_service.disconnect()
        
        return EmailCheckResponse(
            success=True,
            emails_checked=csv_files_found,  # Approximate
            csv_files_found=csv_files_found,
            csv_files_processed=csv_files_processed,
            batches_processed=batches_processed,
            errors=errors
        )
    
    except Exception as e:
        email_service.disconnect()
        logger.error("email_check_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check email: {str(e)}"
        )


@router.post("/process-csv", response_model=BatchProcessResponse)
async def process_batch_csv(
    file: UploadFile = File(...),
    batch_id: Optional[str] = None,
    fontis: FontisClient = Depends(get_fontis_client),
    _: str = Depends(verify_api_key)
):
    """
    Process a declined payment CSV file.
    
    Accepts CSV file upload, processes declined payments, matches customers,
    and sends Day 0 SMS to all matched customers.
    
    CSV filename should match pattern: Batch_{BatchID}_{YYYYMMDDHHMMSS}_result.csv
    If batch_id not provided, will attempt to extract from filename.
    """
    logger.info("batch_csv_upload", filename=file.filename)
    
    # Extract batch ID from filename if not provided
    if not batch_id and file.filename:
        import re
        match = re.search(r'Batch_(\d+)_', file.filename)
        if match:
            batch_id = match.group(1)
    
    if not batch_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="batch_id required. Provide in request or ensure filename matches pattern: Batch_{BatchID}_{timestamp}_result.csv"
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)
    
    try:
        # Process CSV
        orchestrator = BatchOrchestrator(fontis)
        result = await orchestrator.process_batch_csv(tmp_path, batch_id)
        
        return BatchProcessResponse(
            success=result["success"],
            batch_id=batch_id,
            total_records=result["total_records"],
            declined_count=result["declined_count"],
            matched_count=result["matched_count"],
            unmatched_count=result["unmatched_count"],
            sms_sent=result.get("sms_sent", 0),
            sms_failed=result.get("sms_failed", 0),
            message=result.get("message", "Batch processed successfully")
        )
    except Exception as e:
        logger.error("batch_processing_failed", batch_id=batch_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process batch: {str(e)}"
        )
    finally:
        # Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink()


@router.post("/daily-outreach", response_model=DailyOutreachResponse)
async def trigger_daily_outreach(
    batch_id: Optional[str] = None,
    fontis: FontisClient = Depends(get_fontis_client),
    _: str = Depends(verify_api_key)
):
    """
    Trigger daily priority-based outreach processing.
    
    Recalculates priorities for all active declined payment customers
    and triggers appropriate outreach (calls, SMS, email) based on:
    - Next delivery date
    - Account balance status
    - Repeat decline status
    
    Should be called daily via cron job or scheduler.
    """
    logger.info("triggering_daily_outreach", batch_id=batch_id)
    
    try:
        orchestrator = BatchOrchestrator(fontis)
        result = await orchestrator.process_daily_outreach(batch_id=batch_id)
        
        return DailyOutreachResponse(
            success=True,
            **result
        )
    except Exception as e:
        logger.error("daily_outreach_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process daily outreach: {str(e)}"
        )


@router.post("/process-customer/{customer_id}")
async def process_single_customer(
    customer_id: str,
    declined_amount: float = Form(..., description="Declined payment amount"),
    customer_name: str = Form(..., description="Customer name"),
    customer_phone: str = Form(..., description="Customer phone (E.164 format)"),
    delivery_id: Optional[str] = Form(None, description="Delivery ID (optional)"),
    is_repeat_decline: bool = Form(False, description="Is this a repeat decline?"),
    fontis: FontisClient = Depends(get_fontis_client),
    _: str = Depends(verify_api_key)
):
    """
    Process outreach for a single customer.
    
    Calculates priority and triggers appropriate outreach (call/SMS/email)
    based on current account status and delivery schedule.
    """
    logger.info("processing_single_customer", customer_id=customer_id)
    
    try:
        orchestrator = BatchOrchestrator(fontis)
        result = await orchestrator.process_customer_outreach(
            customer_id=customer_id,
            delivery_id=delivery_id,
            declined_amount=declined_amount,
            customer_name=customer_name,
            customer_phone=customer_phone,
            is_repeat_decline=is_repeat_decline,
            batch_id=None
        )
        
        return {
            "success": True,
            "customer_id": customer_id,
            **result
        }
    except Exception as e:
        logger.error("single_customer_processing_failed", customer_id=customer_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process customer: {str(e)}"
        )

