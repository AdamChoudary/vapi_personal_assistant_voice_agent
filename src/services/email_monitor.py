"""
Email monitoring service for CSV batch file detection.

Monitors email inbox for declined payment CSV attachments.
File pattern: Batch_{BatchID}_{YYYYMMDDHHMMSS}_result.csv
"""

import re
import email
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class CSVEmailMonitor:
    """Monitor email for declined payment CSV attachments."""
    
    CSV_PATTERN = re.compile(r'Batch_(\d+)_(\d{14})_result\.csv', re.IGNORECASE)
    
    def __init__(self, download_dir: Path):
        """
        Initialize email monitor.
        
        Args:
            download_dir: Directory to save downloaded CSV files
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.processed_files: set[str] = set()  # Track processed batch IDs
    
    def extract_csv_attachments(
        self,
        email_message: email.message.Message
    ) -> List[Dict[str, any]]:
        """
        Extract CSV attachments from email message.
        
        Args:
            email_message: Parsed email message
        
        Returns:
            List of CSV attachment info:
            {
                "filename": str,
                "batch_id": str,
                "timestamp": datetime,
                "content": bytes
            }
        """
        csv_attachments = []
        
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if not filename:
                    continue
                
                # Check if matches CSV pattern
                match = self.CSV_PATTERN.match(filename)
                if match:
                    batch_id = match.group(1)
                    timestamp_str = match.group(2)
                    
                    # Parse timestamp
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                    except ValueError:
                        logger.warning("invalid_timestamp", filename=filename)
                        continue
                    
                    # Skip if already processed
                    if batch_id in self.processed_files:
                        logger.info("batch_already_processed", batch_id=batch_id)
                        continue
                    
                    # Extract content
                    content = part.get_payload(decode=True)
                    if content:
                        csv_attachments.append({
                            "filename": filename,
                            "batch_id": batch_id,
                            "timestamp": timestamp,
                            "content": content
                        })
        
        return csv_attachments
    
    def save_csv_file(
        self,
        csv_data: Dict[str, any]
    ) -> Path:
        """
        Save CSV attachment to disk.
        
        Args:
            csv_data: CSV attachment data from extract_csv_attachments
        
        Returns:
            Path to saved file
        """
        filename = csv_data["filename"]
        file_path = self.download_dir / filename
        
        with open(file_path, 'wb') as f:
            f.write(csv_data["content"])
        
        logger.info("csv_file_saved", file_path=str(file_path), batch_id=csv_data["batch_id"])
        return file_path
    
    def mark_processed(self, batch_id: str):
        """Mark batch as processed."""
        self.processed_files.add(batch_id)
        logger.info("batch_marked_processed", batch_id=batch_id)
    
    def is_processed(self, batch_id: str) -> bool:
        """Check if batch has been processed."""
        return batch_id in self.processed_files


