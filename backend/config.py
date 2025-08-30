import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from contextlib import contextmanager
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("config")

# Build DB connection string
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
DB_SERVER = os.getenv("DB_SERVER", "10.192.0.180")
DB_NAME = os.getenv("DB_NAME", "vtasdata_amazon")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "m00se_1234")

# URL-encode the driver string to handle spaces
encoded_driver = quote_plus(DB_DRIVER)

CONNECTION_STRING = (
    f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}"
    f"?driver={encoded_driver}"
)
logger.debug("Connection string created successfully")

# Create SQLAlchemy engine
try:
    engine = create_engine(CONNECTION_STRING, echo=False, future=True)
    logger.info("SQLAlchemy engine created successfully")
except Exception as e:
    logger.error(f"Error creating engine: {e}")
    raise

# Create session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def health_check():
    """Verifies database connection by executing a simple query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful for health check")
        return True
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False

@contextmanager
def get_db_connection():
    """
    Provide a transactional scope around a series of operations.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

