import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles SQLite connection and operations for outreach tracking."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Config.DB_PATH
        # Ensure target directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Creates the outreach_log table with required constraints if it does not exist."""
        query = """
        CREATE TABLE IF NOT EXISTS outreach_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            influencer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            message_generated TEXT NOT NULL,
            sent INTEGER NOT NULL,
            sent_at TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(influencer_name, email)
        );
        """
        with self.get_connection() as conn:
            conn.execute(query)
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def is_duplicate(self, influencer_name: str, email: str) -> bool:
        """
        Checks if an outreach record already exists for (influencer_name, email).
        """
        if not email or email == "Not Found":
            return False

        query = "SELECT 1 FROM outreach_log WHERE influencer_name = ? AND email = ? LIMIT 1"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (influencer_name, email))
            return cursor.fetchone() is not None

    def log_outreach(
        self,
        influencer_name: str,
        email: str,
        message: str,
        sent: bool,
        status: str,
    ) -> bool:
        """
        Logs an outreach record into outreach_log table.
        Returns True if inserted successfully, False if duplicate or failed.
        """
        query = """
        INSERT INTO outreach_log (influencer_name, email, message_generated, sent, sent_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            with self.get_connection() as conn:
                conn.execute(
                    query,
                    (influencer_name, email, message, 1 if sent else 0, now_iso, status),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Duplicate outreach attempt blocked by database constraint for {influencer_name} ({email})")
            return False
        except Exception as e:
            logger.error(f"Error logging outreach for {influencer_name}: {e}")
            return False

    def get_all_logs(self) -> List[Dict[str, Any]]:
        """Returns all records from outreach_log table."""
        query = "SELECT * FROM outreach_log ORDER BY id ASC"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
