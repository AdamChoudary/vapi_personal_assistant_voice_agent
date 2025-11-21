"""
Database models and service for declined payment batch tracking.

Tracks:
- Processed CSV batches
- Customer outreach history
- Priority changes over time
- Repeat decline status
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import structlog

logger = structlog.get_logger(__name__)


class BatchRecord:
    """Processed batch record."""
    
    def __init__(
        self,
        batch_id: str,
        processed_at: datetime,
        total_records: int,
        declined_count: int,
        matched_count: int,
        sms_sent: int,
        csv_filename: str
    ):
        self.batch_id = batch_id
        self.processed_at = processed_at
        self.total_records = total_records
        self.declined_count = declined_count
        self.matched_count = matched_count
        self.sms_sent = sms_sent
        self.csv_filename = csv_filename


class CustomerOutreachRecord:
    """Customer outreach tracking record."""
    
    def __init__(
        self,
        customer_id: str,
        batch_id: str,
        declined_amount: float,
        first_declined_at: datetime,
        last_outreach_at: Optional[datetime],
        last_outreach_type: Optional[str],  # "sms", "call", "email"
        current_priority: str,  # "high", "medium", "low"
        is_resolved: bool,
        repeat_decline_count: int
    ):
        self.customer_id = customer_id
        self.batch_id = batch_id
        self.declined_amount = declined_amount
        self.first_declined_at = first_declined_at
        self.last_outreach_at = last_outreach_at
        self.last_outreach_type = last_outreach_type
        self.current_priority = current_priority
        self.is_resolved = is_resolved
        self.repeat_decline_count = repeat_decline_count


class BatchDatabase:
    """SQLite database for batch processing tracking."""
    
    def __init__(self, db_path: Path):
        """
        Initialize database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Processed batches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_batches (
                    batch_id TEXT PRIMARY KEY,
                    processed_at TEXT NOT NULL,
                    total_records INTEGER NOT NULL,
                    declined_count INTEGER NOT NULL,
                    matched_count INTEGER NOT NULL,
                    sms_sent INTEGER NOT NULL,
                    csv_filename TEXT NOT NULL
                )
            """)
            
            # Customer outreach tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customer_outreach (
                    customer_id TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    declined_amount REAL NOT NULL,
                    first_declined_at TEXT NOT NULL,
                    last_outreach_at TEXT,
                    last_outreach_type TEXT,
                    current_priority TEXT NOT NULL,
                    is_resolved INTEGER NOT NULL DEFAULT 0,
                    repeat_decline_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (customer_id, batch_id),
                    FOREIGN KEY (batch_id) REFERENCES processed_batches(batch_id)
                )
            """)
            
            # Outreach history table (for detailed tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outreach_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    outreach_type TEXT NOT NULL,
                    outreach_date TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    call_id TEXT,
                    sms_id TEXT,
                    success INTEGER NOT NULL DEFAULT 1,
                    error_message TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_outreach_customer_id 
                ON customer_outreach(customer_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_outreach_priority 
                ON customer_outreach(current_priority)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_customer_outreach_resolved 
                ON customer_outreach(is_resolved)
            """)
            
            conn.commit()
            logger.info("database_schema_initialized", db_path=str(self.db_path))
    
    def record_batch_processed(
        self,
        batch_id: str,
        total_records: int,
        declined_count: int,
        matched_count: int,
        sms_sent: int,
        csv_filename: str
    ):
        """Record that a batch has been processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO processed_batches
                (batch_id, processed_at, total_records, declined_count, matched_count, sms_sent, csv_filename)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                datetime.now().isoformat(),
                total_records,
                declined_count,
                matched_count,
                sms_sent,
                csv_filename
            ))
            logger.info("batch_recorded", batch_id=batch_id)
    
    def is_batch_processed(self, batch_id: str) -> bool:
        """Check if batch has been processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_batches WHERE batch_id = ?", (batch_id,))
            return cursor.fetchone() is not None
    
    def record_customer_decline(
        self,
        customer_id: str,
        batch_id: str,
        declined_amount: float,
        priority: str
    ):
        """Record customer decline and check for repeat."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if customer has declined before
            cursor.execute("""
                SELECT repeat_decline_count FROM customer_outreach
                WHERE customer_id = ? AND batch_id != ?
                ORDER BY first_declined_at DESC LIMIT 1
            """, (customer_id, batch_id))
            
            existing = cursor.fetchone()
            repeat_count = (existing["repeat_decline_count"] + 1) if existing else 0
            
            # Insert or update customer record
            cursor.execute("""
                INSERT OR REPLACE INTO customer_outreach
                (customer_id, batch_id, declined_amount, first_declined_at, current_priority, is_resolved, repeat_decline_count)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """, (
                customer_id,
                batch_id,
                declined_amount,
                datetime.now().isoformat(),
                priority,
                repeat_count
            ))
            
            logger.info(
                "customer_decline_recorded",
                customer_id=customer_id,
                batch_id=batch_id,
                repeat_count=repeat_count
            )
    
    def record_outreach(
        self,
        customer_id: str,
        batch_id: str,
        outreach_type: str,
        priority: str,
        call_id: Optional[str] = None,
        sms_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Record outreach attempt."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert into history
            cursor.execute("""
                INSERT INTO outreach_history
                (customer_id, batch_id, outreach_type, outreach_date, priority, call_id, sms_id, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id,
                batch_id,
                outreach_type,
                datetime.now().isoformat(),
                priority,
                call_id,
                sms_id,
                1 if success else 0,
                error_message
            ))
            
            # Update customer record
            cursor.execute("""
                UPDATE customer_outreach
                SET last_outreach_at = ?, last_outreach_type = ?, current_priority = ?
                WHERE customer_id = ? AND batch_id = ?
            """, (
                datetime.now().isoformat(),
                outreach_type,
                priority,
                customer_id,
                batch_id
            ))
            
            logger.info(
                "outreach_recorded",
                customer_id=customer_id,
                outreach_type=outreach_type,
                success=success
            )
    
    def mark_customer_resolved(self, customer_id: str, batch_id: str):
        """Mark customer as resolved (payment received)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE customer_outreach
                SET is_resolved = 1
                WHERE customer_id = ? AND batch_id = ?
            """, (customer_id, batch_id))
            logger.info("customer_marked_resolved", customer_id=customer_id, batch_id=batch_id)
    
    def get_active_declined_customers(
        self,
        batch_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all active (unresolved) declined customers."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if batch_id:
                cursor.execute("""
                    SELECT * FROM customer_outreach
                    WHERE batch_id = ? AND is_resolved = 0
                    ORDER BY current_priority DESC, first_declined_at ASC
                """, (batch_id,))
            else:
                cursor.execute("""
                    SELECT * FROM customer_outreach
                    WHERE is_resolved = 0
                    ORDER BY current_priority DESC, first_declined_at ASC
                """)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def is_repeat_decline(self, customer_id: str, batch_id: str) -> bool:
        """Check if customer has declined before."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM customer_outreach
                WHERE customer_id = ? AND batch_id != ?
            """, (customer_id, batch_id))
            result = cursor.fetchone()
            return result["count"] > 0
    
    def get_customer_outreach_history(
        self,
        customer_id: str,
        batch_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get outreach history for a customer."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if batch_id:
                cursor.execute("""
                    SELECT * FROM outreach_history
                    WHERE customer_id = ? AND batch_id = ?
                    ORDER BY outreach_date DESC
                """, (customer_id, batch_id))
            else:
                cursor.execute("""
                    SELECT * FROM outreach_history
                    WHERE customer_id = ?
                    ORDER BY outreach_date DESC
                """, (customer_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


