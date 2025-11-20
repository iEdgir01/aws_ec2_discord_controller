"""Structured logging configuration for EC2 Discord Bot

Provides JSON-formatted logs for better aggregation and analysis.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "command"):
            log_data["command"] = record.command
        if hasattr(record, "instance_id"):
            log_data["instance_id"] = record.instance_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data)


def setup_logging(log_file: str = "/data/ec2bot.log", level: str = "INFO") -> logging.Logger:
    """Configure structured logging for the bot

    Args:
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("ec2bot")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    # File handler with JSON formatting if path exists
    log_path = Path(log_file)
    if log_path.parent.exists():
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    # Configure Discord.py logging
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.INFO)
    discord_logger.addHandler(console_handler)

    logger.info("Logging initialized", extra={"log_level": level})

    return logger


def log_command(logger: logging.Logger, command: str, user_id: int, **kwargs):
    """Log a Discord command execution

    Args:
        logger: Logger instance
        command: Command name
        user_id: Discord user ID
        **kwargs: Additional context
    """
    logger.info(
        f"Command executed: {command}",
        extra={"command": command, "user_id": user_id, **kwargs}
    )


def log_aws_operation(logger: logging.Logger, operation: str, instance_id: str, duration_ms: float, success: bool = True):
    """Log an AWS operation

    Args:
        logger: Logger instance
        operation: Operation name (e.g., "start_instance", "stop_instance")
        instance_id: EC2 instance ID
        duration_ms: Operation duration in milliseconds
        success: Whether operation succeeded
    """
    level = logging.INFO if success else logging.ERROR
    logger.log(
        level,
        f"AWS operation: {operation} on {instance_id}",
        extra={
            "operation": operation,
            "instance_id": instance_id,
            "duration_ms": duration_ms,
            "success": success
        }
    )
