import json
import os
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder

from . import __version__
from .api import router
from .config import get_settings
from .db import Base, engine
from .request_context import request_id_var

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(message)s",
)
logger = logging.getLogger("feedback_engine")

app = FastAPI(
    title="Feedback Intelligence Engine",
    version=__version__,
    description="Evidence-grounded product feedback synthesis and human review API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "test" else settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")

WEB_DIR = Path(os.getenv("WEB_DIR", str(Path(__file__).resolve().parent / "web")))
if WEB_DIR.exists():
    app.mount("/app", StaticFiles(directory=WEB_DIR), name="app")

    @app.get("/", include_in_schema=False)
    def web_index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-Id"] = request_id
        return response
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            json.dumps(
                {
                    "event": "http.request.completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
                separators=(",", ":"),
            )
        )
        request_id_var.reset(token)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request could not be completed."
    body = {
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": message,
            "request_id": request_id_var.get(),
        }
    }
    if not isinstance(detail, str):
        body["error"]["details"] = jsonable_encoder(detail)
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": jsonable_encoder(exc.errors()),
                "request_id": request_id_var.get(),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        json.dumps(
            {
                "event": "http.request.failed",
                "request_id": request_id_var.get(),
                "path": request.url.path,
                "error_type": type(exc).__name__,
            }
        )
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error.",
                "request_id": request_id_var.get(),
            }
        },
    )


def run() -> None:
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "feedback_intelligence_engine.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    run()
