from fastapi import APIRouter
from backend.routes.metrics_store import snapshot

router = APIRouter()

@router.get("/")
async def get_metrics():
    snap = snapshot()
    models = snap.get("models", {})
    total_calls = sum(m.get("count", 0) for m in models.values())
    return {
        "total_calls": total_calls,
        "models": models,
    }