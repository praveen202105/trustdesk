import hmac
from decimal import Decimal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .config import settings
from .db import SessionLocal
from .ingest import checksum
from .jobs import advisory
from .models import MockEffect, uid

app = FastAPI(title="TrustDesk mock world", docs_url=None, redoc_url=None)

class ReviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: str = Field(max_length=200)
    reason: str = Field(min_length=1, max_length=1000)
    amount: Decimal = Field(gt=0)
    idempotency_key: str = Field(max_length=200)

@app.get("/health")
def health():
    return {"status":"ok", "mode":"mock-actions"}

@app.post("/internal/refund-reviews")
def review(body: ReviewBody, x_action_secret: str = Header(default=""), idempotency_key: str = Header(default="")):
    if not hmac.compare_digest(x_action_secret, settings.mock_action_secret):
        raise HTTPException(401, "ACTION_AUTH_REQUIRED")
    if not idempotency_key or idempotency_key != body.idempotency_key:
        raise HTTPException(422, "IDEMPOTENCY_KEY_REQUIRED")
    payload_hash = checksum(body.model_dump(mode="json"))
    with SessionLocal.begin() as session:
        advisory(session, "mock-effect:" + idempotency_key)
        existing = session.get(MockEffect, idempotency_key)
        if existing:
            if existing.payload_hash != payload_hash:
                raise HTTPException(409, "IDEMPOTENCY_CONFLICT")
            return existing.result
        result = {"external_review_id": "review_" + uid(), "status": "review_requested", "money_refunded": False}
        session.add(MockEffect(id=idempotency_key, namespace="demo", payload_hash=payload_hash, result=result))
        return result
