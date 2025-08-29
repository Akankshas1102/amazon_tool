from fastapi import FastAPI
from routes import router

app = FastAPI(title="Amazon Project API")

# Register routes
app.include_router(router)

@app.get("/")
def root():
    return {"message": "Amazon Project API running with JSON storage"}
