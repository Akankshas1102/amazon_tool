import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router as device_router
from config import health_check
from services.scheduler_service import start_scheduler
from services.cache_service import set_cache_value  # Import cache service
from logger import get_logger

# Create the logger instance at the top of the file
logger = get_logger(__name__)
app = FastAPI(title="Amazon Device Control API")

# Start the scheduler on application startup
@app.on_event("startup")
def startup_event():
    logger.info("Application startup event triggered.")
    
    # Initialize the global panel status (default to Armed)
    try:
        set_cache_value('panel_armed', True)
        logger.info("Global panel status initialized to 'Armed'.")
    except Exception as e:
        logger.error(f"Failed to initialize panel status in cache: {e}")
        
    start_scheduler()

# This section gives your frontend permission to access the backend
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add the /api prefix to all routes from routes.py
app.include_router(device_router, prefix="/api")

@app.get("/health")
def health():
    """
    Provides a simple health check for the service.
    """
    logger.info("Health check endpoint was called.")
    is_healthy = health_check()
    
    if is_healthy:
        logger.info("Database health check successful.")
    else:
        logger.warning("Database health check failed.")
        
    return {"status": "ok" if is_healthy else "error",
            "datastore": "accessible" if is_healthy else "inaccessible"}

@app.get("/")
def root():
    """
    Root endpoint with a welcome message.
    """
    logger.info("Root endpoint was called.")
    return {"message": "Welcome to the Amazon Device Control API"}

# This block allows the script to be run directly and starts the server.
if __name__ == "__main__":
    logger.info("Starting Uvicorn server.")
    uvicorn.run(app, host="127.0.0.1", port=8000)