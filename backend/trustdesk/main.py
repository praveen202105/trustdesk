from fastapi import FastAPI

from .config import settings

app = FastAPI(title="TrustDesk", version="0.1.0")

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "mode": settings.ai_provider, "revision": settings.revision}
