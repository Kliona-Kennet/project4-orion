# backend/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from routes import upload, inference, metrics
from config.cors import add_cors
from storage import init_db

# -----------------------------
# App Initialization
# -----------------------------
app = FastAPI(
    title="AFL Vision Backend",
    version="1.0.0",
    description="Backend API for AFL Vision Insight project "
                "(Upload, Inference, Metrics)."
)

# -----------------------------
# Startup Event (DB init, etc.)
# -----------------------------
@app.on_event("startup")
async def startup_event():
    init_db()  # ensure tables exist (uploads, inferences, etc.)

# -----------------------------
# CORS Middleware
# -----------------------------
# Allow React dev server & future prod builds
add_cors(app)

# -----------------------------
# Global Middleware
# -----------------------------
@app.middleware("http")
async def api_version_header(request: Request, call_next):
    """Attach API version header to every response."""
    response = await call_next(request)
    response.headers["X-API-Version"] = "1"
    return response

# -----------------------------
# Healthcheck Root
# -----------------------------
@app.get("/", tags=["Health"])
def read_root():
    return {
        "status": "success",
        "message": "AFL Vision Backend Running",
        "version": "1.0.0"
    }

# -----------------------------
# Routers
# -----------------------------
app.include_router(upload.router,    prefix="/api/v1/upload",   tags=["Upload"])
app.include_router(inference.router, prefix="/api/v1/inference", tags=["Inference"])
app.include_router(metrics.router,   prefix="/api/v1/metrics",  tags=["Metrics"])