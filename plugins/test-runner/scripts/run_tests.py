#!/usr/bin/env python3
"""
PostToolUse Hook: Automatic Test Runner
Triggers test execution when source/test files are modified.
Runs tests in background to avoid blocking Claude Code.
"""

import json
import logging
import sys
import os
import subprocess
import fcntl
import time
from pathlib import Path
from typing import Optional

from shared.logging import get_logger

# Configuration via environment variables
TEST_COMMAND = os.environ.get("CLAUDE_TEST_COMMAND", "")
TEST_TIMEOUT = int(os.environ.get("CLAUDE_TEST_TIMEOUT", "60"))
DEBOUNCE_SECONDS = int(os.environ.get("CLAUDE_TEST_DEBOUNCE", "5"))
TEST_ENABLED = os.environ.get("CLAUDE_TEST_ENABLED", "1") == "1"

# Module-level logger (initialized lazily)
_logger: logging.Logger | None = None


def get_plugin_logger(log_dir: Path) -> logging.Logger:
    """Initialize and return the logger for the test-runner plugin."""
    global _logger
    if _logger is None:
        log_file = log_dir / "test-runner.jsonl"
        _logger = get_logger("test-runner", log_file)
    return _logger


def get_log_dir(cwd: str) -> Path:
    """Create and return the log directory for test runs."""
    log_dir = Path(cwd) / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def should_debounce(log_dir: Path) -> bool:
    """Check if we should skip this run due to recent execution."""
    last_run_file = log_dir / ".last_run"
    if last_run_file.exists():
        try:
            last_run = float(last_run_file.read_text().strip())
            if time.time() - last_run < DEBOUNCE_SECONDS:
                return True
        except (ValueError, IOError):
            pass
    return False


def update_last_run(log_dir: Path) -> None:
    """Update the timestamp of the last test run."""
    (log_dir / ".last_run").write_text(str(time.time()))


def acquire_lock(lock_file: Path) -> Optional[int]:
    """Acquire an exclusive lock to prevent concurrent test runs."""
    try:
        fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except (OSError, IOError):
        return None


def release_lock(fd: int) -> None:
    """Release the lock file."""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    except (OSError, IOError):
        pass


def run_tests_background(command: str, cwd: str, log_dir: Path, logger: logging.Logger) -> None:
    """Fork and run tests in background process."""
    pid = os.fork()
    if pid > 0:
        return  # Parent returns immediately

    # Child process runs tests
    try:
        os.setsid()
        logger.info("Test run started", extra={"event": "test_started", "command": command})
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            timeout=TEST_TIMEOUT,
            text=True,
            shell=True
        )
        status = "passed" if result.returncode == 0 else "failed"
        logger.info("Test run completed", extra={
            "event": "test_completed",
            "status": status,
            "return_code": result.returncode
        })
    except subprocess.TimeoutExpired:
        logger.error("Tests timeout", extra={"event": "test_timeout", "timeout_seconds": TEST_TIMEOUT})
    except Exception as e:
        logger.error("Tests error", extra={"event": "test_error", "error": str(e)})
    finally:
        os._exit(0)


def main() -> int:
    """Main entry point for the hook."""
    # Early exit if disabled or no command configured
    if not TEST_ENABLED or not TEST_COMMAND:
        return 0

    # Parse stdin JSON
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 1

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    cwd = input_data.get("cwd", os.getcwd())

    # Only trigger on Edit or Write tools
    if tool_name not in ("Edit", "Write"):
        return 0

    file_path = tool_input.get("file_path", "")
    log_dir = get_log_dir(cwd)

    # Initialize logger after log_dir is created
    logger = get_plugin_logger(log_dir)

    # Debounce and locking
    if should_debounce(log_dir):
        return 0

    lock_file = log_dir / ".lock"
    lock_fd = acquire_lock(lock_file)
    if lock_fd is None:
        return 0

    try:
        update_last_run(log_dir)
        logger.info("Test triggered", extra={"event": "test_triggered", "file_path": file_path})
        run_tests_background(TEST_COMMAND, cwd, log_dir, logger)
    finally:
        release_lock(lock_fd)

    return 0


if __name__ == "__main__":
    sys.exit(main())
