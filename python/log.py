import os # Need this to grab dir obj

# For logging
import logging 
from logging.handlers import RotatingFileHandler

# For data in logging
import datetime
import json

# For logging path
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent

def setup_logging():
    """
    Fire up logging
    
    things that are allowed to change
    log_path
    """
    
    log_path = PROMPT_DIR / "logs"
    
    # Create logs directory if not exists
    os.makedirs(log_path, exist_ok=True)

    # LOG_LEVEL from env: DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
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
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            # Add request_id if attached by middleware
            if hasattr(record, "request_id"):
                base["request_id"] = getattr(record, "request_id")
            # Add HTTP context for 404 and other HTTP errors
            if hasattr(record, "http_method"):
                base["http_method"] = getattr(record, "http_method")
            if hasattr(record, "http_path"):
                base["http_path"] = getattr(record, "http_path")
            if hasattr(record, "http_status"):
                base["http_status"] = getattr(record, "http_status")
            if hasattr(record, "query_params"):
                base["query_params"] = getattr(record, "query_params")
            if hasattr(record, "client_ip"):
                base["client_ip"] = getattr(record, "client_ip")
            if hasattr(record, "content_type"):
                base["content_type"] = getattr(record, "content_type")
            if hasattr(record, "user_agent"):
                base["user_agent"] = getattr(record, "user_agent")
            if hasattr(record, "referer"):
                base["referer"] = getattr(record, "referer")
            if hasattr(record, "available_routes"):
                base["available_routes"] = getattr(record, "available_routes")
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
    fh = RotatingFileHandler(log_path / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    root_logger.addHandler(fh)

    # Dedicated error log handler with full stack traces
    class ErrorFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            error_msg = f"""
================================================================================
ERROR DETAILS
================================================================================
Timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}
Level: {record.levelname}
Logger: {record.name}
Message: {record.getMessage()}
"""
            # Add request_id if available
            if hasattr(record, "request_id") and record.request_id:
                error_msg += f"Request ID: {record.request_id}\n"
            
            # Add HTTP context if available
            if hasattr(record, "http_method"):
                error_msg += f"HTTP Method: {getattr(record, 'http_method')}\n"
            if hasattr(record, "http_path"):
                error_msg += f"HTTP Path: {getattr(record, 'http_path')}\n"
            if hasattr(record, "client_ip"):
                error_msg += f"Client IP: {getattr(record, 'client_ip')}\n"
            
            # Add full stack trace if exception
            if record.exc_info:
                error_msg += f"""
Stack Trace:
{self.formatException(record.exc_info)}
"""
            
            error_msg += "================================================================================\n"
            return error_msg

    error_formatter = ErrorFormatter()
    efh = RotatingFileHandler(log_path / "error.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    efh.setLevel(logging.ERROR)
    efh.setFormatter(error_formatter)
    root_logger.addHandler(efh)

    # Tame noisy loggers but keep uvicorn access/error
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    for noisy in ("httpx", "openai", "asyncio", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
