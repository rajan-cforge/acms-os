"""Logging utilities for MCP server."""
import functools
import logging
from typing import Callable, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('acms.mcp')


def log_mcp_call(func: Callable) -> Callable:
    """
    Decorator to log MCP tool calls with inputs, outputs, and errors.

    Usage:
        @log_mcp_call
        @mcp.tool()
        async def my_tool(param: str) -> dict:
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        tool_name = func.__name__

        # Log entry
        logger.info(f"MCP CALL START: {tool_name}")
        logger.debug(f"  Args: {args}")
        logger.debug(f"  Kwargs: {kwargs}")

        try:
            # Execute tool
            result = await func(*args, **kwargs)

            # Log success
            logger.info(f"MCP CALL SUCCESS: {tool_name}")
            logger.debug(f"  Result: {result}")

            return result

        except Exception as e:
            # Log error
            logger.error(f"MCP CALL ERROR: {tool_name}")
            logger.error(f"  Exception: {type(e).__name__}: {e}")

            # Re-raise to be handled by tool
            raise

    return wrapper
