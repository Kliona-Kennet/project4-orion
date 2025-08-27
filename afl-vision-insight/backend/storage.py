from __future__ import annotations

import os, uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from dotenv import load_dotenv

# --- Load .env explicitly from project root (…/afl-vision-insight/.env) ---
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT / ".env")

# --- Read & normalize DATABASE_URL (force psycopg v3 driver name) ---
DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if DATABASE_URL.startswith("postgresql+psycopg2"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2", "postgresql+psycopg", 1)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not set. Put it in afl-vision-insight/.env, e.g.\n"
        "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/aflvision"
    )

from sqlalchemy import create_engine, func, String, Integer, DateTime
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

# --- SQLAlchemy engine/session ---
# psycopg v3 is the DBAPI when using +psycopg.
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass

# --- ORM models ---
class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False, default="video")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Inference(Base):
    __tablename__ = "inferences"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    task: Mapped[str] = mapped_column(String(16), nullable=False)  # "player" | "crowd"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# Create tables automatically (quick start; prefer Alembic migrations later)
Base.metadata.create_all(bind=engine)

# --- DB helpers used by routes ---
def _db():
    return SessionLocal()

def save_upload(path: str, media_type: str, size_bytes: int) -> dict:
    with _db() as db:
        row = Upload(path=path, media_type=media_type, size_bytes=size_bytes)
        db.add(row); db.commit(); db.refresh(row)
        return {
            "id": str(row.id),
            "path": row.path,
            "media_type": row.media_type,
            "size_bytes": row.size_bytes,
            "created_at": row.created_at.isoformat()
        }

def get_upload(upload_id: str) -> Optional[dict]:
    from sqlalchemy.exc import NoResultFound
    with _db() as db:
        try:
            row = db.query(Upload).filter(Upload.id == uuid.UUID(upload_id)).one()
            return {
                "id": str(row.id),
                "path": row.path,
                "media_type": row.media_type,
                "size_bytes": row.size_bytes,
                "created_at": row.created_at.isoformat()
            }
        except NoResultFound:
            return None

def save_inference(upload_id: str, task: str, status: str, payload: Dict[str, Any]) -> dict:
    with _db() as db:
        row = Inference(upload_id=uuid.UUID(upload_id), task=task, status=status, payload=payload or {})
        db.add(row); db.commit(); db.refresh(row)
        return {
            "id": str(row.id),
            "upload_id": str(row.upload_id),
            "task": row.task,
            "status": row.status,
            "payload": row.payload,
            "created_at": row.created_at.isoformat()
        }

def list_inferences(limit: int = 50) -> List[dict]:
    with _db() as db:
        rows = db.query(Inference).order_by(Inference.created_at.desc()).limit(limit).all()
        return [{
            "id": str(r.id),
            "upload_id": str(r.upload_id),
            "task": r.task,
            "status": r.status,
            "payload": r.payload,
            "created_at": r.created_at.isoformat()
        } for r in rows]

def inferences_summary() -> dict:
    with _db() as db:
        total  = db.query(func.count(Inference.id)).scalar() or 0
        player = db.query(func.count(Inference.id)).filter(Inference.task == "player").scalar() or 0
        crowd  = db.query(func.count(Inference.id)).filter(Inference.task == "crowd").scalar() or 0
        last   = db.query(Inference).order_by(Inference.created_at.desc()).first()
        last_payload = None
        if last:
            last_payload = {
                "id": str(last.id),
                "upload_id": str(last.upload_id),
                "task": last.task,
                "status": last.status,
                "payload": last.payload,
                "created_at": last.created_at.isoformat()
            }
        return {"total": total, "by_task": {"player": player, "crowd": crowd}, "last": last_payload}

def init_db() -> None:
    # ensure tables exist and connection is healthy
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")