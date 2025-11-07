"""
Email integration service for CSV batch file monitoring.

Monitors email inbox for declined payment CSV attachments.
Supports IMAP for receiving emails.
"""

import email
import imaplib
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import structlog

from src.services.email_monitor import CSVEmailMonitor

logger = structlog.get_logger(__name__)


class EmailIntegrationService:
    """Email service for monitoring CSV batch files."""
    
    def __init__(
        self,
        imap_server: str,
        imap_port: int,
        email_address: str,
        email_password: str,
        download_dir: Path
    ):
        """
        Initialize email integration service.
        
        Args:
            imap_server: IMAP server hostname (e.g., "imap.gmail.com")
            imap_port: IMAP port (usually 993 for SSL)
            email_address: Email address to monitor
            email_password: Email password or app password
            download_dir: Directory to save CSV files
        """
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.email_address = email_address
        self.email_password = email_password
        self.monitor = CSVEmailMonitor(download_dir)
        self._imap_connection: Optional[imaplib.IMAP4_SSL] = None
    
    async def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            self._imap_connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self._imap_connection.login(self.email_address, self.email_password)
            logger.info("email_connected", server=self.imap_server)
            return True
        except Exception as e:
            logger.error("email_connection_failed", error=str(e))
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server."""
        if self._imap_connection:
            try:
                self._imap_connection.close()
                self._imap_connection.logout()
            except Exception:
                pass
            finally:
                self._imap_connection = None
    
    async def check_for_new_csvs(
        self,
        folder: str = "INBOX",
        since_date: Optional[datetime] = None
    ) -> List[Dict[str, any]]:
        """
        Check email inbox for new CSV attachments.
        
        Args:
            folder: Email folder to check (default: INBOX)
            since_date: Only check emails since this date
        
        Returns:
            List of CSV file info dictionaries
        """
        if not self._imap_connection:
            if not await self.connect():
                return []
        
        try:
            self._imap_connection.select(folder)
            
            # Build search criteria
            search_criteria = "ALL"
            if since_date:
                date_str = since_date.strftime("%d-%b-%Y")
                search_criteria = f'SINCE "{date_str}"'
            
            # Search for emails
            status, message_numbers = self._imap_connection.search(None, search_criteria)
            if status != "OK":
                logger.error("email_search_failed", status=status)
                return []
            
            csv_files = []
            message_ids = message_numbers[0].split()
            
            for msg_id in message_ids:
                try:
                    # Fetch email
                    status, msg_data = self._imap_connection.fetch(msg_id, "(RFC822)")
                    if status != "OK":
                        continue
                    
                    # Parse email
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Extract CSV attachments
                    attachments = self.monitor.extract_csv_attachments(email_message)
                    
                    for attachment in attachments:
                        # Save CSV file
                        file_path = self.monitor.save_csv_file(attachment)
                        csv_files.append({
                            **attachment,
                            "file_path": file_path,
                            "email_id": msg_id.decode()
                        })
                
                except Exception as e:
                    logger.error("email_processing_error", msg_id=msg_id, error=str(e))
                    continue
            
            logger.info("csv_check_complete", found_count=len(csv_files))
            return csv_files
        
        except Exception as e:
            logger.error("csv_check_failed", error=str(e))
            return []
    
    async def mark_email_read(self, email_id: str, folder: str = "INBOX"):
        """Mark email as read."""
        if not self._imap_connection:
            return
        
        try:
            self._imap_connection.select(folder)
            self._imap_connection.store(email_id, "+FLAGS", "\\Seen")
        except Exception as e:
            logger.error("mark_read_failed", email_id=email_id, error=str(e))


