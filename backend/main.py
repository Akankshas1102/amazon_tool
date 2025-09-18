import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # ✅ correct import
from routes import router as device_router
from config import health_check

app = FastAPI(title="Amazon Device Control API")

# ✅ Allow requests from your frontend (127.0.0.1:5500)
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # frontend URLs allowed
    allow_credentials=True,
    allow_methods=["*"],          # allow all HTTP methods
    allow_headers=["*"],          # allow all headers
)

# Add the /api prefix to all routes from routes.py
app.include_router(device_router, prefix="/api")

@app.get("/health")
def health():
    """
    Provides a simple health check for the service.
    """
    is_healthy = health_check()
    return {"status": "ok" if is_healthy else "error", 
            "datastore": "accessible" if is_healthy else "inaccessible"}

@app.get("/")
def root():
    """
    Root endpoint with a welcome message.
    """
    return {"message": "Welcome to the Amazon Device Control API"}

# This block allows the script to be run directly and starts the server.
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
