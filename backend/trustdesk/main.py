import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .api import actor, router
from .config import settings
from .db import engine

app = FastAPI(title="TrustDesk", version="0.1.0", docs_url=None, redoc_url=None)
app.include_router(router)


@app.middleware("http")
async def protect(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    public = request.url.path == "/api/v1/health" or (
        request.url.path == "/api/v1/auth/session" and request.method == "POST")
    try:
        if not public:
            request.state.actor = actor(request)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("origin") != settings.app_origin:
                raise HTTPException(403, "ORIGIN_REJECTED")
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 256 * 1024:
                    raise HTTPException(413, "REQUEST_TOO_LARGE")
            request._body = bytes(body)
        response = await call_next(request)
    except HTTPException as exc:
        response = error_response(request, exc.status_code, str(exc.detail), exc.headers)
    except SQLAlchemyError:
        response = error_response(request, 503, "DATABASE_UNAVAILABLE")
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def error_response(request: Request, status: int, code: str, headers=None):
    return JSONResponse(status_code=status, headers=headers,
                        content={"error": {"code": code, "message": code.replace("_", " ").capitalize(),
                                           "request_id": getattr(request.state, "request_id", ""), "details": {}}})


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return error_response(request, exc.status_code, str(exc.detail), exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return error_response(request, 422, "VALIDATION_ERROR")


@app.get("/api/v1/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, detail="DATABASE_UNAVAILABLE") from None
    return {"status": "ok", "mode": settings.ai_provider, "revision": settings.revision}
