"""
This File ONLY STORE API ROUTE. NOTHING ELSE
"""

# For Request ID 
import uuid

# Logging
import logging

# dotenv for loading .env
import os
from dotenv import load_dotenv

# Fast api for api implementation
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

# OpenAi for Connect OpenAI and chatting with AI
from openai import OpenAI

# Server and Port
import uvicorn

# Self
from helper import _grab_system_prompt, _format_response
from log import setup_logging
import llm

# Grab .env items
load_dotenv()

# Grab prompt
prompt = _grab_system_prompt(0)
# =========
# Logging Setup
# =========

setup_logging()
logger = logging.getLogger("app")

# =========
# FastAPI App
# =========

app = FastAPI(title="Product Type Identifier Web Search Agent API", version="1.1.0")

# =========
# Middleware: Request ID & Structured Access Logs
# =========

@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    # Create a new request id
    request_id: str = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    # Attach to request state so handlers can use it if needed
    request.state.request_id = request_id

    # Log inbound request (avoid logging sensitive headers)
    logger.info(
        f"Incoming request {request.method} {request.url.path}",
        extra={"request_id": request_id},
    )
    
    try:
        response = await call_next(request)
    except Exception:
        # Let exception handlers log details; still ensure we add request_id to log record
        logger.exception("Unhandled exception during request", extra={"request_id": request_id})
        raise

    # Add X-Request-ID to response for correlation
    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"Completed request {request.method} {request.url.path} -> {response.status_code}",
        extra={"request_id": request_id},
    )
    return response

# =========
# Exception Handlers
# =========
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # Log as warning for 4xx, error for 5xx
    lvl = logging.WARNING if 400 <= exc.status_code < 500 else logging.ERROR
    logger.log(
        lvl,
        f"HTTPException: {exc.status_code} {exc.detail}",
        extra={"request_id": getattr(request.state, 'request_id', None)},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            },
            "request_id": getattr(request.state, 'request_id', None)
        },
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Full stack trace
    logger.exception(
        "Unhandled server error",
        extra={"request_id": getattr(request.state, 'request_id', None)},
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": {
                "code": 500,
                "message": "Internal server error"
            },
            "request_id": getattr(request.state, 'request_id', None)
        },
    )

# =========
# Routes
# =========
@app.get("/health")
async def health_check() -> JSONResponse:
    """_summary_
    Health Check for openai and the app itself
    Returns:
        JSONResponse: {
            status_code: int
            content: {
                status: str
                openai: str
            }
        }
    Example Output:
    {
        status_code=200,
        content={
            "status": "healthy",
            "openai": "connected",
        },
    }
    """
    openai_ok: bool
    detail: str | None
    openai_ok, detail = llm.health_check_openai(timeout=5)
    
    # Return ok if openai is ok
    if openai_ok:
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "openai": "connected",
            },
        )

    # Return failed and log
    logger.warning("Health check failed: OpenAI not reachable")
    return JSONResponse(
        status_code=503,
        content={
            "status": "unhealthy",
            "openai": "not connected",
            "detail": detail or "OpenAI connectivity check failed",
        },
    )


@app.post("/input/")
async def post_input(
    request: Request,
    text: str | None = Query(None, description="Text query as query parameter"),
) -> JSONResponse:
    """
    User input API
    Accept query parameter first, then JSON body, then error if empty.
    
    Args:
        request (Request): fastapi request. DO NOT TOUCH
        text (str | None, optional): _description_. Defaults to Query(None, description="Text query as query parameter").

    Returns:
        JSONResponse: _description_
    """
    # Step 1: Grab request_id
    request_id = getattr(request.state, 'request_id', None)
    if text:
        logger.info("Received input from query", extra={"request_id": request_id, "user_input_text": text})
    # Step 2: If missing or empty, fallback to body JSON
    else:
        try:
            # Grab user_input from params
            if request.headers.get("content-type", "").startswith("application/json"):
                body = await request.json()
                text = body.get("text")
                
                # Step 3: If still empty → error
                if not text:
                    raise HTTPException(
                        status_code=400,
                        detail="No text provided. Provide ?text=... or JSON body {\"text\": \"...\"}"
                    )
                
                logger.info("Received input from body", extra={"request_id": request_id, "user_input_text": text})
        except Exception:
            # ignore invalid json; error thrown below if still empty
            text = None
            return JSONResponse (
                status_code=404,
                content={
                    "status": "error",
                    "input": "null",
                    "output": "null",
                    "request_id": request_id
                }
            )

    # Log the received input
    logger.info("Received input", extra={"request_id": request_id, "user_input_text": text})

    llm.setup()
    # OpenAI call
    try:
        # Past input to openai 
        output = llm.send_input(prompt=prompt, user_input=text)
        logger.info("OpenAI API call success", extra={"request_id": request_id, "user_input_text": text})
    except Exception as e:
        # Don’t expose internals to clients; log details server-side
        logger.exception(f"OpenAI API call failed {e}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=503,
            detail=f"OpenAI service error. Error: {e}"
        ) from e

    if not output:
        logger.error("Empty response from OpenAI", extra={"request_id": request_id})
        raise HTTPException(status_code=502, detail="Empty response from OpenAI")

    formatted_output: str = _format_response(output)

    return JSONResponse (
        status_code=200,
        content={
            "status": "ok",
            "input": text,
            "output": formatted_output if formatted_output else "null",
            "request_id": request_id
        }
    )


# =========
# OpenAPI / Swagger UI
# =========

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# redirect "/" -> "/docs" (place with other routes)
@app.get("/", include_in_schema=False)
async def root(request: Request):
    return RedirectResponse(url=request.url_for("swagger_ui"), status_code=307)

# Swagger API Documentation
@app.get("/docs", include_in_schema=False)
async def swagger_ui():
    return get_swagger_ui_html(openapi_url=app.openapi_url, title=f"{app.title} - Swagger UI")

# REDOC API Documentation
@app.get("/redoc", include_in_schema=False)
async def redoc_ui():
    return get_redoc_html(openapi_url=app.openapi_url, title=f"{app.title} - ReDoc")

# =========
# Entrypoint
# =========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # NOTE: uvicorn access logs are helpful; keep them on for ops visibility
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=port,
        reload=True
    )