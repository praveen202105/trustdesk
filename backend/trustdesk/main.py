from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from .config import settings
from .db import engine

app = FastAPI(title="TrustDesk", version="0.1.0")

@app.get("/api/v1/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, detail="DATABASE_UNAVAILABLE") from None
    return {"status": "ok", "mode": settings.ai_provider, "revision": settings.revision}
