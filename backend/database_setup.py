import sqlite3
import os
from logger import get_logger

logger = get_logger(__name__)

# The name of your database file
SQLITE_DB_PATH = "building_schedules.db"

def init_sqlite_db():
    """
    Completely rebuilds the SQLite database with the correct schema.
    This will delete all existing data.
    """
    # Safety check to ensure we are in the correct directory
    if os.path.basename(os.getcwd()) != 'backend':
        print("Please run this script from the 'backend' directory.")
        return

    # Delete the old database file if it exists
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
        logger.info(f"Removed old database file: {SQLITE_DB_PATH}")

    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            logger.info("Creating new database and tables...")

            # Table for building schedules
            conn.execute("""
                CREATE TABLE building_times (
                    building_id INTEGER PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Trigger to update the updated_at timestamp
            conn.execute("""
                CREATE TRIGGER update_building_times_timestamp
                AFTER UPDATE ON building_times
                BEGIN
                    UPDATE building_times SET updated_at = CURRENT_TIMESTAMP
                    WHERE building_id = NEW.building_id;
                END
            """)

            # CORRECTED: Table for ignored proevents with new columns
            conn.execute("""
                CREATE TABLE ignored_proevents (
                    proevent_id INTEGER PRIMARY KEY,
                    building_frk INTEGER NOT NULL,
                    device_prk INTEGER NOT NULL,
                    ignore_on_arm BOOLEAN NOT NULL DEFAULT 0,
                    ignore_on_disarm BOOLEAN NOT NULL DEFAULT 0
                )
            """)

            # CORRECTED: Table for ProEvent state history with new column
            conn.execute("""
                CREATE TABLE proevent_state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proevent_id INTEGER NOT NULL,
                    building_frk INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
        logger.info("SQLite database initialized successfully with the correct schema.")
        print("\nDatabase setup complete")

    except Exception as e:
        logger.error(f"Error initializing SQLite database: {e}")
        print(f"\nAn error occurred: {e}")
        raise

if __name__ == "__main__":
    init_sqlite_db()