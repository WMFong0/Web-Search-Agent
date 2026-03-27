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
    fh = RotatingFileHandler(log_path / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    root_logger.addHandler(fh)

    # Tame noisy loggers but keep uvicorn access/error
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    for noisy in ("httpx", "openai", "asyncio", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
