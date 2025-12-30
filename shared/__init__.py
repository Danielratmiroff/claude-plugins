"""
Shared utilities for Claude Code plugins.

This package provides common functionality shared across plugins,
including standardized JSONL logging.
"""

from shared.logging import get_logger, log_event

__all__ = ["get_logger", "log_event"]
