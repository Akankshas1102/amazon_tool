# backend/sqlite_config.py

import sqlite3
from contextlib import contextmanager
from logger import get_logger

logger = get_logger(__name__)

SQLITE_DB_PATH = "building_schedules.db"

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

def get_building_time(building_id: int) -> dict | None:
    # ... (this function remains the same)
    with get_sqlite_connection() as conn:
        cursor = conn.execute(
            "SELECT start_time, end_time FROM building_times WHERE building_id = ?",
            (building_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

def set_building_time(building_id: int, start_time: str, end_time: str | None) -> bool:
    # ... (this function remains the same)
    try:
        with get_sqlite_connection() as conn:
            conn.execute("""
                INSERT INTO building_times (building_id, start_time, end_time)
                VALUES (?, ?, ?)
                ON CONFLICT(building_id) DO UPDATE SET 
                    start_time = excluded.start_time,
                    end_time = excluded.end_time,
                    updated_at = CURRENT_TIMESTAMP
            """, (building_id, start_time, end_time))
        logger.info(f"Building {building_id} scheduled time updated to {start_time} - {end_time}")
        return True
    except Exception as e:
        logger.error(f"Error setting building time: {e}")
        return False

def get_all_building_times() -> dict:
    # ... (this function remains the same)
    with get_sqlite_connection() as conn:
        cursor = conn.execute("SELECT building_id, start_time, end_time FROM building_times")
        return {row["building_id"]: {"start_time": row["start_time"], "end_time": row["end_time"]} for row in cursor.fetchall()}

# --- Ignored ProEvent Functions ---

def get_ignored_proevents() -> list[int]:
    """Get all proevent IDs from the ignored_proevents table."""
    with get_sqlite_connection() as conn:
        cursor = conn.execute("SELECT proevent_id FROM ignored_proevents")
        return [row["proevent_id"] for row in cursor.fetchall()]

def add_ignored_proevent(proevent_id: int) -> bool:
    """Add a proevent to the ignored_proevents table."""
    try:
        with get_sqlite_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO ignored_proevents (proevent_id) VALUES (?)", (proevent_id,))
        logger.info(f"ProEvent {proevent_id} added to ignored list.")
        return True
    except Exception as e:
        logger.error(f"Error adding ignored proevent for ID {proevent_id}: {e}")
        return False

def remove_ignored_proevent(proevent_id: int) -> bool:
    """Remove a proevent from the ignored_proevents table."""
    try:
        with get_sqlite_connection() as conn:
            conn.execute("DELETE FROM ignored_proevents WHERE proevent_id = ?", (proevent_id,))
        logger.info(f"ProEvent {proevent_id} removed from ignored list.")
        return True
    except Exception as e:
        logger.error(f"Error removing ignored proevent for ID {proevent_id}: {e}")
        return False