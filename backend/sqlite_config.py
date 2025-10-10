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

def get_ignored_proevents() -> dict:
    """Get all proevent ignore settings."""
    with get_sqlite_connection() as conn:
        cursor = conn.execute("SELECT proevent_id, ignore_on_arm, ignore_on_disarm FROM ignored_proevents")
        # Return a dictionary for easy lookup
        return {row["proevent_id"]: {"ignore_on_arm": bool(row["ignore_on_arm"]), "ignore_on_disarm": bool(row["ignore_on_disarm"])} for row in cursor.fetchall()}

def set_proevent_ignore_status(proevent_id: int, ignore_on_arm: bool, ignore_on_disarm: bool) -> bool:
    """Set the ignore status for a specific proevent."""
    try:
        with get_sqlite_connection() as conn:
            conn.execute("""
                INSERT INTO ignored_proevents (proevent_id, ignore_on_arm, ignore_on_disarm)
                VALUES (?, ?, ?)
                ON CONFLICT(proevent_id) DO UPDATE SET
                    ignore_on_arm = excluded.ignore_on_arm,
                    ignore_on_disarm = excluded.ignore_on_disarm
            """, (proevent_id, ignore_on_arm, ignore_on_disarm))
        logger.info(f"Updated ignore status for ProEvent {proevent_id}")
        return True
    except Exception as e:
        logger.error(f"Error setting ignore status for ProEvent ID {proevent_id}: {e}")
        return False

# --- ProEvent History Logging ---

def log_proevent_state(proevent_id: int, state: str) -> bool:
    """Log a ProEvent's state change to the history table."""
    try:
        with get_sqlite_connection() as conn:
            conn.execute(
                "INSERT INTO proevent_state_history (proevent_id, state) VALUES (?, ?)",
                (proevent_id, state)
            )
        logger.info(f"Logged state '{state}' for ProEvent {proevent_id}")
        return True
    except Exception as e:
        logger.error(f"Error logging ProEvent state for ID {proevent_id}: {e}")
        return False