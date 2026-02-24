# Python Package Included
import os
import json
import uuid
from datetime import datetime

# Logging
import logging
from logging.handlers import RotatingFileHandler

# dotenv for loading .env
from dotenv import load_dotenv

# Fast api for api implementation
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

# OpenAi for Connect OpenAI and chatting with AI
from openai import OpenAI

# Allow Optional Parameter
from typing import Optional

# Server and Port
import uvicorn



# =========
# Bootstrapping
# =========
load_dotenv()

# =========
# Logging Setup
# =========
def setup_logging():
    # Create logs directory if not exists
    os.makedirs("logs", exist_ok=True)

    # LOG_LEVEL from env: DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level, logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove default handlers to avoid duplicates if reload=True
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    # Formatter (JSON-ish single-line)
    class JsonLikeFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            base = {
                "ts": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            # Add request_id if attached by middleware
            if hasattr(record, "request_id"):
                base["request_id"] = getattr(record, "request_id")
            # Add exception info if present
            if record.exc_info:
                base["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(base, ensure_ascii=False)

    formatter = JsonLikeFormatter()

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    # Rotating file handler
    fh = RotatingFileHandler("logs/app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    root_logger.addHandler(fh)

    # Tame noisy loggers but keep uvicorn access/error
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    for noisy in ("httpx", "openai", "asyncio", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger("app")

# =========
# FastAPI App
# =========
app = FastAPI(title="Product Type Identifier Web Search Agent API", version="1.0.0")

prompt = """Help the user identify products type related to a given abbreviation or term available in Mannings HK or SaSa HK retail store. Return the top results in the format specified.

# Steps
1. Review the user query and focus on identifying products type referenced by the term or abbreviation they provide (e.g., "BOH").
2. Cross-reference the provided term against a hypothetical database or knowledge base of health and beauty products available at Mannings HK or SaSa HK.
3. Select and return the top results that match the term, with clarity and relevance being prioritized.
4. Format the response in the structure requested by the user (e.g., `product type1, product type2, product type3`).

# Output Format
- Return the list of products type as a CSV (Comma-Separated Value) string with no additional text or formatting.
- Example format for the output: `product type1, product type2, product type3`

# Examples
**Input:**
"BOH"

**Repharsed Input**
Hi. I'm a Hong Kong customer looking forward to buy health and beauty products that are available in Mannings HK or SaSa HK retail store. Can you tell what products type does "BOH" refer to? Give out the top result in the csv file format: product1, product2, product3.
**Output:**
Lifting Cream, Honey Mask, Green Tea Essence
User query: """

# =========
# Middleware: Request ID & Structured Access Logs
# =========
@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    # Create a new request id
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
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
async def http_exception_handler(request: Request, exc: HTTPException):
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
async def unhandled_exception_handler(request: Request, exc: Exception):
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
# Utilities
# =========
def format_response(response: str) -> Optional[str]:
    """Format the output response to the top CSV item only."""
    try:
        cleaned = response.replace("\n", "").strip()
        if not cleaned:
            return None
        items = [item.strip() for item in cleaned.split(",") if item.strip()]
        return items[0] if items else None
    except Exception:
        logger.exception("Error formatting response")
        return None

# =========
# Routes
# =========
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/input/")
async def post_input(
    request: Request,
    text: Optional[str] = Query(None, description="Text query as query parameter"),
):
    """Accept query parameters, send to OpenAI Responses API, and return the model's response."""
    request_id = getattr(request.state, 'request_id', None)

    # Grab from body if no text query exist
    if not text:
        try:
            if request.headers.get("content-type","").startswith("application/json"):
                body = await request.json()
                provided_text = body.get("text")
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No text provided. Please provide 'text' as a query parameter (e.g., ?text=BOH)"
                )
        except Exception as e:
            logger.exception("Empty Query and Empty Body received", extra={"request_id": request_id})
    logger.info("Received input", extra={"request_id": request_id, "user_input_text": text})

    # Environment setup
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "Michael-Web-Search-Test")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

    # Validate required settings without leaking secrets in logs
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Azure OpenAI API key not configured. Please check environment variables."
        )
    if not endpoint:
        raise HTTPException(
            status_code=500,
            detail="Azure OpenAI endpoint not configured. Please check environment variables."
        )

    client = OpenAI(base_url=endpoint, api_key=api_key)

    # OpenAI call
    try:
        completion = client.responses.create(
            model=deployment_name,
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {
                        "type": "approximate",
                        "country": "HK"
                    }
                }
            ],
            input=prompt + text,
            timeout=30,
            max_output_tokens=75
        )

        logger.info("OpenAI API call success", extra={"request_id": request_id, "user_input_text": text})
        output = getattr(completion, "output_text", None)

    except Exception as e:
        # Don’t expose internals to clients; log details server-side
        logger.exception("OpenAI API call failed", extra={"request_id": request_id})
        raise HTTPException(
            status_code=503,
            detail="OpenAI service error"
        ) from e

    if not output:
        logger.error("Empty response from OpenAI", extra={"request_id": request_id})
        raise HTTPException(status_code=502, detail="Empty response from OpenAI")

    formatted_output = format_response(output)

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