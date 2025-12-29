#!/usr/bin/env python3
"""
PostToolUse Hook: Automatic Test Runner
Triggers test execution when source/test files are modified.
Runs tests in background to avoid blocking Claude Code.
"""

import json
import sys
import os
import subprocess
import fcntl
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Configuration via environment variables
TEST_COMMAND = ".claude/hooks/run_all_tests.sh"
TEST_TIMEOUT = 60
DEBOUNCE_SECONDS = 5
TEST_ENABLED = True


def get_log_dir(cwd: str) -> Path:
    """Create and return the log directory for test runs."""
    log_dir = Path(cwd) / ".claude" / "logs" / "test-runner"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def log_message(log_dir: Path, message: str) -> None:
    """Append a timestamped message to the log file."""
    log_file = log_dir / "test_runs.log"
    timestamp = datetime.now().isoformat()
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


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


def run_tests_background(command: str, cwd: str, log_dir: Path) -> None:
    """Fork and run tests in background process."""
    log_file = log_dir / "test_runs.log"
    pid = os.fork()
    if pid > 0:
        return  # Parent returns immediately

    # Child process runs tests
    try:
        os.setsid()
        with open(log_file, "a") as log:
            log.write(f"\n{'='*60}\n")
            log.write(f"[{datetime.now().isoformat()}] Running: {command}\n")
            log.write(f"{'='*60}\n")
            log.flush()
            result = subprocess.run(
                command,
                cwd=cwd,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=TEST_TIMEOUT,
                text=True,
                shell=True
            )
            status = "PASSED" if result.returncode == 0 else f"FAILED (exit {result.returncode})"
            log.write(f"\n[{datetime.now().isoformat()}] Tests {status}\n")
    except subprocess.TimeoutExpired:
        log_message(log_dir, f"Tests TIMEOUT after {TEST_TIMEOUT}s")
    except Exception as e:
        log_message(log_dir, f"Tests ERROR: {e}")
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

    # Debounce and locking
    if should_debounce(log_dir):
        return 0

    lock_file = log_dir / ".lock"
    lock_fd = acquire_lock(lock_file)
    if lock_fd is None:
        return 0

    try:
        update_last_run(log_dir)
        log_message(log_dir, f"Triggered by: {file_path}")
        run_tests_background(TEST_COMMAND, cwd, log_dir)
    finally:
        release_lock(lock_fd)

    return 0


if __name__ == "__main__":
    sys.exit(main())
