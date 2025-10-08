import sqlite3
import os
from contextlib import contextmanager
from logger import get_logger

logger = get_logger(__name__)

SQLITE_DB_PATH = "building_schedules.db"

def init_sqlite_db():
    """Initialize SQLite database and create tables if they don't exist."""
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            # Table for building schedules
            conn.execute("""
                CREATE TABLE IF NOT EXISTS building_times (
                    building_id INTEGER PRIMARY KEY,
                    scheduled_time TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Trigger to update the updated_at timestamp for building_times
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_building_times_timestamp 
                AFTER UPDATE ON building_times
                BEGIN
                    UPDATE building_times SET updated_at = CURRENT_TIMESTAMP 
                    WHERE building_id = NEW.building_id;
                END
            """)

            # New table for ignored alarms
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ignored_alarms (
                    device_id INTEGER PRIMARY KEY
                )
            """)
            
            conn.commit()
        logger.info("SQLite database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing SQLite database: {e}")
        raise

@contextmanager
def get_sqlite_connection():
    """Context manager for SQLite database connections."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        logger.error(f"SQLite transaction error: {e}")
        raise
    else:
        conn.commit()
    finally:
        conn.close()

# --- Building Schedule Functions ---

def get_building_time(building_id: int) -> str | None:
    """Get scheduled time for a building."""
    with get_sqlite_connection() as conn:
        cursor = conn.execute(
            "SELECT scheduled_time FROM building_times WHERE building_id = ?",
            (building_id,)
        )
        row = cursor.fetchone()
        return row["scheduled_time"] if row else None

def set_building_time(building_id: int, scheduled_time: str) -> bool:
    """Set scheduled time for a building."""
    try:
        with get_sqlite_connection() as conn:
            conn.execute("""
                INSERT INTO building_times (building_id, scheduled_time)
                VALUES (?, ?)
                ON CONFLICT(building_id) DO UPDATE SET 
                    scheduled_time = excluded.scheduled_time,
                    updated_at = CURRENT_TIMESTAMP
            """, (building_id, scheduled_time))
        logger.info(f"Building {building_id} scheduled time updated to {scheduled_time}")
        return True
    except Exception as e:
        logger.error(f"Error setting building time: {e}")
        return False

def get_all_building_times() -> dict:
    """Get all building scheduled times."""
    with get_sqlite_connection() as conn:
        cursor = conn.execute("SELECT building_id, scheduled_time FROM building_times")
        return {row["building_id"]: row["scheduled_time"] for row in cursor.fetchall()}

# --- Ignored Alarm Functions ---

def get_ignored_alarms() -> list[int]:
    """Get all device IDs from the ignored_alarms table."""
    with get_sqlite_connection() as conn:
        cursor = conn.execute("SELECT device_id FROM ignored_alarms")
        return [row["device_id"] for row in cursor.fetchall()]

def add_ignored_alarm(device_id: int) -> bool:
    """Add a device to the ignored_alarms table."""
    try:
        with get_sqlite_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO ignored_alarms (device_id) VALUES (?)", (device_id,))
        logger.info(f"Device {device_id} added to ignored alarms.")
        return True
    except Exception as e:
        logger.error(f"Error adding ignored alarm for device {device_id}: {e}")
        return False

def remove_ignored_alarm(device_id: int) -> bool:
    """Remove a device from the ignored_alarms table."""
    try:
        with get_sqlite_connection() as conn:
            conn.execute("DELETE FROM ignored_alarms WHERE device_id = ?", (device_id,))
        logger.info(f"Device {device_id} removed from ignored alarms.")
        return True
    except Exception as e:
        logger.error(f"Error removing ignored alarm for device {device_id}: {e}")
        return False

# Initialize database on module import
init_sqlite_db()