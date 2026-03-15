"""Structured logging configuration for Kinsu Health API.

This module provides a centralized logging setup with:
- JSON-formatted structured logs for production
- Human-readable logs for development
- Context injection (request_id, user_id, etc.)
- Integration with FastAPI
"""

import logging
import sys
from typing import Any, Dict, Optional
import json
from datetime import datetime
from contextvars import ContextVar

from app.core.config import settings


# Context variables for request-scoped data
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with additional context."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields passed to the logger
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and context."""
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Base format
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        log_line = (
            f"{color}{self.BOLD}[{record.levelname:^8}]{self.RESET} "
            f"{timestamp} | {record.name} | "
            f"{record.getMessage()}"
        )

        # Add context if available
        context_parts = []
        request_id = request_id_var.get()
        if request_id:
            context_parts.append(f"req={request_id[:8]}")
        
        user_id = user_id_var.get()
        if user_id:
            context_parts.append(f"user={user_id[:8]}")

        if context_parts:
            log_line += f" [{', '.join(context_parts)}]"

        # Add exception if present
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)

        return log_line


def setup_logging(log_level: str = "INFO", use_json: bool = False) -> None:
    """Configure application-wide logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: If True, use JSON structured logging; otherwise use development format
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter based on mode
    if use_json:
        formatter = StructuredFormatter()
    else:
        formatter = DevelopmentFormatter()
    
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Set levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding extra context to log messages."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Process log message and add extra fields."""
        extra = kwargs.get("extra", {})
        
        # Merge adapter's extra with call-specific extra
        if self.extra:
            extra.update(self.extra)
        
        # Store extra fields in a way that our formatter can access
        if extra:
            kwargs["extra"] = {"extra_fields": extra}
        
        return msg, kwargs


def get_logger_with_context(name: str, **context: Any) -> LoggerAdapter:
    """Get a logger with persistent context fields.
    
    Args:
        name: Logger name (typically __name__)
        **context: Additional context to include in all log messages
    
    Returns:
        LoggerAdapter with context
    
    Example:
        logger = get_logger_with_context(__name__, service="vitals")
        logger.info("Processing vital", extra={"vital_type": "heart_rate"})
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context)
