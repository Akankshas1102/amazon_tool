# backend/database_setup.py

import sqlite3
import os
from logger import get_logger

logger = get_logger(__name__)

SQLITE_DB_PATH = "building_schedules.db"

def init_sqlite_db():
    """Initialize SQLite database and create tables if they don't exist."""
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            # Drop existing tables for a clean setup
            conn.execute("DROP TABLE IF EXISTS building_times")
            conn.execute("DROP TABLE IF EXISTS ignored_alarms")
            conn.execute("DROP TABLE IF EXISTS ignored_proevents") # Drop old tables if they exist
            
            # Table for building schedules
            conn.execute("""
                CREATE TABLE IF NOT EXISTS building_times (
                    building_id INTEGER PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Trigger to update the updated_at timestamp
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_building_times_timestamp 
                AFTER UPDATE ON building_times
                BEGIN
                    UPDATE building_times SET updated_at = CURRENT_TIMESTAMP 
                    WHERE building_id = NEW.building_id;
                END
            """)

            # New, more detailed table for ignored proevents
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ignored_proevents (
                    proevent_id INTEGER PRIMARY KEY,
                    ignore_on_arm BOOLEAN NOT NULL DEFAULT 0,
                    ignore_on_disarm BOOLEAN NOT NULL DEFAULT 0
                )
            """)
            
            # New table for ProEvent state history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proevent_state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proevent_id INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        logger.info("SQLite database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing SQLite database: {e}")
        raise

if __name__ == "__main__":
    init_sqlite_db()