import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Auto-Patent Architect API", version="1.0.0")

# CORS - must be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure output directories exist
os.makedirs("temp", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("samples", exist_ok=True)

# Mount static files for output access
app.mount("/output", StaticFiles(directory="output"), name="output")

# Import and include router
from api.routes import router
app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Auto-Patent Architect API is running", "version": "1.0.0"}
