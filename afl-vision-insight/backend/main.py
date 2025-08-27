from dotenv import load_dotenv
load_dotenv()

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.routes import upload, inference, metrics
from backend.config.cors import add_cors
from backend.config.logging import setup_logging, RequestLoggerMiddleware
from backend.storage import init_db

API_PREFIX = "/api/v1"
API_VERSION = "1"

def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(title="AFL Vision Backend", version=API_VERSION)

    init_db()

    add_cors(app)

    app.add_middleware(RequestLoggerMiddleware)

    @app.middleware("http")
    async def api_version_header(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-API-Version"] = API_VERSION
        return resp

    @app.get(f"{API_PREFIX}/health")
    def health():
        return {"ok": True, "version": int(API_VERSION)}

    @app.get("/")
    def read_root():
        return {"message": "AFL Vision Backend Running"}

    app.include_router(upload.router,    prefix=f"{API_PREFIX}/upload",    tags=["Upload"])
    app.include_router(inference.router, prefix=f"{API_PREFIX}/inference", tags=["Inference"])
    app.include_router(metrics.router,   prefix=f"{API_PREFIX}/metrics",   tags=["Metrics"])

    return app

app = create_app()