"""
Structured Logging with Correlation IDs

Production-grade logging infrastructure for request tracing.

Features:
- Correlation IDs for tracking requests across services
- JSON format for log aggregation (Datadog, CloudWatch, etc.)
- Context propagation through async calls
- FastAPI middleware integration

Implementation Status: COMPLETE
Week 5 Day 1: Task 1 (2 hours)
"""

import logging
import json
import uuid
import time
from contextvars import ContextVar
from typing import Optional
from datetime import datetime

# Context variable for correlation ID (thread-safe for async)
correlation_id_ctx: ContextVar[str] = ContextVar('correlation_id', default='')

logger = logging.getLogger(__name__)


def get_correlation_id() -> str:
    """
    Get current correlation ID from context.

    If no correlation ID is set, generates a new UUID.

    Returns:
        str: Correlation ID (UUID format)
    """
    corr_id = correlation_id_ctx.get()
    if not corr_id:
        corr_id = str(uuid.uuid4())
        correlation_id_ctx.set(corr_id)
    return corr_id


def set_correlation_id(correlation_id: str):
    """
    Set correlation ID in context.

    Args:
        correlation_id: Correlation ID to set (usually from X-Correlation-ID header)
    """
    correlation_id_ctx.set(correlation_id)


class CorrelationIDFilter(logging.Filter):
    """
    Logging filter that adds correlation ID to all log records.

    This ensures every log line includes the correlation ID,
    making it easy to trace requests across services.
    """

    def filter(self, record):
        """
        Add correlation_id attribute to log record.

        Args:
            record: LogRecord to modify

        Returns:
            bool: True (always accept the record)
        """
        record.correlation_id = get_correlation_id()
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    Outputs logs in JSON format for easy parsing by log aggregation tools.
    """

    def format(self, record):
        """
        Format log record as JSON.

        Args:
            record: LogRecord to format

        Returns:
            str: JSON-formatted log line
        """
        # Build log data dictionary
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'correlation_id': getattr(record, 'correlation_id', 'no-correlation-id'),
            'module': record.name,
            'message': record.getMessage()
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields from logger.info(..., extra={...})
        # Skip standard LogRecord attributes
        skip_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'pathname', 'process', 'processName', 'relativeCreated',
            'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
            'correlation_id'
        }

        for key, value in record.__dict__.items():
            if key not in skip_attrs and not key.startswith('_'):
                log_data[key] = value

        return json.dumps(log_data)


def setup_logging(
    stream=None,
    format: str = 'json',
    level: str = 'INFO'
):
    """
    Configure structured logging for production.

    Args:
        stream: Output stream (default: stderr)
        format: Log format ('json' or 'text')
        level: Log level (default: 'INFO')
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Clear existing handlers
    root_logger.handlers.clear()

    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Create handler
    if stream is None:
        handler = logging.StreamHandler()
    else:
        handler = logging.StreamHandler(stream)

    handler.setLevel(log_level)

    # Set formatter based on format
    if format == 'json':
        formatter = JSONFormatter()
    else:
        # Text format with correlation ID
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(correlation_id)s] - %(name)s - %(message)s'
        )

    handler.setFormatter(formatter)

    # Add correlation ID filter
    correlation_filter = CorrelationIDFilter()
    handler.addFilter(correlation_filter)

    # Add handler to root logger
    root_logger.addHandler(handler)

    # Suppress noisy library loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('weaviate').setLevel(logging.WARNING)

    # Don't log during setup to avoid polluting test output
    # logger.info("Structured logging configured", extra={
    #     'format': format,
    #     'level': level
    # })


# FastAPI middleware for correlation IDs
async def correlation_middleware(request, call_next):
    """
    FastAPI middleware to add correlation IDs to requests.

    Features:
    - Extracts correlation ID from X-Correlation-ID header
    - Generates new UUID if not provided
    - Adds correlation ID to response headers
    - Logs request start/completion with timing

    Args:
        request: FastAPI Request
        call_next: Next middleware/endpoint

    Returns:
        Response with X-Correlation-ID header
    """
    # Get or generate correlation ID
    correlation_id = request.headers.get('X-Correlation-ID')
    if not correlation_id:
        correlation_id = str(uuid.uuid4())

    # Set in context
    set_correlation_id(correlation_id)

    # Log request start
    logger.info(
        "Request started",
        extra={
            'method': request.method,
            'path': request.url.path,
            'client': request.client.host if request.client else 'unknown'
        }
    )

    start_time = time.time()

    try:
        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log completion
        logger.info(
            "Request completed",
            extra={
                'status_code': response.status_code,
                'duration_ms': round(duration_ms, 2)
            }
        )

        # Add correlation ID to response
        response.headers['X-Correlation-ID'] = correlation_id

        return response

    except Exception as e:
        # Log exception
        duration_ms = (time.time() - start_time) * 1000

        logger.error(
            f"Request failed: {str(e)}",
            extra={
                'exception_type': type(e).__name__,
                'duration_ms': round(duration_ms, 2)
            },
            exc_info=True
        )

        # Re-raise to let FastAPI handle it
        raise
