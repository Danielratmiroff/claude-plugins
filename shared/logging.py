"""
Shared JSONL logging module for Claude Code plugins.

Provides a thin wrapper around python-json-logger for consistent
JSONL output across all plugins.

Usage:
    from shared.logging import get_logger

    logger = get_logger("bash-safety", Path(".claude/logs/bash-safety.jsonl"))
    logger.warning("Blocked command", extra={
        "event": "command_blocked",
        "command": cmd,
        "reasons": [...]
    })
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pythonjsonlogger import jsonlogger


class PluginJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that adds plugin name and ISO timestamp to every log record."""

    def __init__(self, plugin_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin_name = plugin_name

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        # Add ISO 8601 timestamp with timezone
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        # Rename levelname to level
        if "levelname" in log_record:
            log_record["level"] = log_record.pop("levelname")
        # Add plugin name to every log entry
        log_record["plugin"] = self.plugin_name
        # Ensure event field exists (default to log level name if not provided)
        if "event" not in log_record:
            log_record["event"] = record.levelname.lower()


def get_logger(
    plugin_name: str,
    log_file: Path,
    level: int = logging.DEBUG,
    max_bytes: Optional[int] = None,
) -> logging.Logger:
    """
    Create and configure a logger for a plugin.

    Args:
        plugin_name: Identifier for the plugin (e.g., "bash-safety", "observability")
        log_file: Path to the JSONL log file
        level: Logging level (default: DEBUG)
        max_bytes: Optional max file size before rotation (not implemented yet)

    Returns:
        Configured logger instance
    """
    # Create logger with plugin-specific name to avoid conflicts
    logger = logging.getLogger(f"claude-plugin.{plugin_name}")
    logger.setLevel(level)

    # Avoid duplicate handlers if get_logger is called multiple times
    if logger.handlers:
        return logger

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create file handler
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setLevel(level)

    # Configure JSON formatter
    # Format string includes levelname so it's available in add_fields
    formatter = PluginJsonFormatter(
        plugin_name,
        "%(levelname)s %(message)s",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def log_event(
    logger: logging.Logger,
    level: int,
    message: str,
    event: str,
    **kwargs,
) -> None:
    """
    Convenience function to log an event with standard fields.

    Args:
        logger: Logger instance from get_logger()
        level: Logging level (e.g., logging.INFO, logging.WARNING)
        message: Human-readable message
        event: Event type in snake_case (e.g., "command_blocked", "test_completed")
        **kwargs: Additional plugin-specific fields
    """
    logger.log(level, message, extra={"event": event, **kwargs})
