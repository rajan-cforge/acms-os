"""
Structured logging for MCP agents
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any


class AgentLogger:
    """Structured logging for agents"""

    def __init__(self, agent_name: str, log_level: int = logging.INFO):
        self.agent_name = agent_name
        self.logger = logging.getLogger(agent_name)
        self.logger.setLevel(log_level)

        # Console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'[{agent_name}] %(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_action(self, action: str, details: Dict[str, Any]):
        """Log agent action with structured data"""
        log_entry = {
            "agent": self.agent_name,
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.info(json.dumps(log_entry))

    def log_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Log tool invocation"""
        self.log_action("tool_call", {
            "tool": tool_name,
            "args": arguments
        })

    def log_error(self, error: str, context: Dict[str, Any] = None):
        """Log error with context"""
        log_entry = {
            "agent": self.agent_name,
            "error": error,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        self.logger.error(json.dumps(log_entry))

    def log_completion(self, task: str, duration_seconds: float = None):
        """Log task completion"""
        details = {"task": task}
        if duration_seconds:
            details["duration_seconds"] = duration_seconds
        self.log_action("completed", details)

    def info(self, message: str):
        """Simple info log"""
        self.logger.info(message)

    def debug(self, message: str):
        """Simple debug log"""
        self.logger.debug(message)

    def warning(self, message: str):
        """Simple warning log"""
        self.logger.warning(message)

    def error(self, message: str):
        """Simple error log"""
        self.logger.error(message)
