"""Trace ID Generation and Propagation for ACMS Gateway.

Provides request-level tracing through all layers of the pipeline.
Every request gets a unique trace_id that follows it through:
- API entry point
- All log statements
- SSE events
- Database queries
- External API calls

Usage:
    from src.gateway.tracing import generate_trace_id, get_trace_id, set_trace_id

    # At request entry:
    trace_id = generate_trace_id()
    set_trace_id(trace_id)

    # Anywhere in the request lifecycle:
    current_trace = get_trace_id()
    logger.info(f"[{current_trace}] Processing query...")
"""

import uuid
import logging
from contextvars import ContextVar
from typing import Optional
from functools import wraps

logger = logging.getLogger(__name__)

# ContextVar for thread-safe trace ID propagation
# Works correctly with async/await
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')


def generate_trace_id() -> str:
    """Generate a new unique trace ID.

    Returns:
        str: Short but unique trace ID (8 chars from UUID)

    Format: First 8 characters of a UUID4, e.g., "a1b2c3d4"
    This provides 16^8 = 4.3 billion unique IDs, sufficient for tracing.
    """
    return str(uuid.uuid4())[:8]


def get_trace_id() -> str:
    """Get the current trace ID from context.

    Returns:
        str: Current trace ID, or empty string if not set

    This is safe to call from any async task - ContextVar handles
    the async context correctly.
    """
    return trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """Set the trace ID for the current context.

    Args:
        trace_id: The trace ID to set (usually from generate_trace_id())

    This should be called once at the entry point of each request.
    The trace ID will automatically propagate to all async tasks
    spawned from this context.
    """
    trace_id_var.set(trace_id)


def clear_trace_id() -> None:
    """Clear the trace ID from context.

    Call this at the end of request processing if needed,
    though typically the ContextVar will be cleaned up automatically
    when the request completes.
    """
    trace_id_var.set('')


class TraceContext:
    """Context manager for automatic trace ID management.

    Usage:
        async def handle_request(query: str):
            with TraceContext() as trace_id:
                logger.info(f"[{trace_id}] Processing query: {query}")
                # All code here has access to trace_id via get_trace_id()
    """

    def __init__(self, trace_id: Optional[str] = None):
        """Initialize trace context.

        Args:
            trace_id: Optional pre-generated trace ID. If None, generates new one.
        """
        self.trace_id = trace_id or generate_trace_id()
        self.token = None

    def __enter__(self) -> str:
        """Enter context and set trace ID."""
        self.token = trace_id_var.set(self.trace_id)
        return self.trace_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous trace ID."""
        if self.token:
            trace_id_var.reset(self.token)


def with_trace_id(func):
    """Decorator to ensure a function has a trace ID.

    If no trace ID is set in context, generates a new one.
    If trace ID already exists, uses the existing one.

    Usage:
        @with_trace_id
        async def process_query(query: str):
            trace_id = get_trace_id()  # Always available
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current = get_trace_id()
        if not current:
            with TraceContext() as trace_id:
                logger.debug(f"[{trace_id}] Auto-generated trace ID for {func.__name__}")
                return await func(*args, **kwargs)
        return await func(*args, **kwargs)
    return wrapper


def log_with_trace(level: int, message: str, **kwargs):
    """Log a message with the current trace ID automatically prepended.

    Args:
        level: Logging level (e.g., logging.INFO)
        message: Log message
        **kwargs: Additional context to log

    Usage:
        log_with_trace(logging.INFO, "Processing query", query_length=100)
        # Output: [a1b2c3d4] Processing query | query_length=100
    """
    trace_id = get_trace_id()
    prefix = f"[{trace_id}] " if trace_id else ""

    if kwargs:
        extra = " | " + " ".join(f"{k}={v}" for k, v in kwargs.items())
    else:
        extra = ""

    logger.log(level, f"{prefix}{message}{extra}")


# Convenience functions for common log levels
def trace_debug(message: str, **kwargs):
    """Debug log with trace ID."""
    log_with_trace(logging.DEBUG, message, **kwargs)


def trace_info(message: str, **kwargs):
    """Info log with trace ID."""
    log_with_trace(logging.INFO, message, **kwargs)


def trace_warning(message: str, **kwargs):
    """Warning log with trace ID."""
    log_with_trace(logging.WARNING, message, **kwargs)


def trace_error(message: str, **kwargs):
    """Error log with trace ID."""
    log_with_trace(logging.ERROR, message, **kwargs)
