#!/usr/bin/env python3
"""Tests for simplified run_tests hook."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Add the scripts directory to the path - navigate from tests/test-runner/ to plugins/test-runner/scripts/
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "plugins" / "test-runner" / "scripts"))

# Import the module under test
import run_tests


class TestConfiguration:
    """Test configuration handling."""

    def test_disabled_when_test_enabled_false(self):
        """Test that hook exits early when TEST_ENABLED is falsy."""
        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "test.py"},
            "cwd": "/tmp"
        }

        with patch.object(run_tests, "TEST_ENABLED", False):
            with patch("sys.stdin", StringIO(json.dumps(input_data))):
                result = run_tests.main()

        assert result == 0

    def test_no_command_exits_early(self):
        """Test that hook exits early when no test command is configured."""
        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "test.py"},
            "cwd": "/tmp"
        }

        with patch.object(run_tests, "TEST_ENABLED", True):
            with patch.object(run_tests, "TEST_COMMAND", ""):
                with patch("sys.stdin", StringIO(json.dumps(input_data))):
                    result = run_tests.main()

        assert result == 0

    def test_default_timeout_is_int(self):
        """Test that TEST_TIMEOUT has correct default value."""
        assert run_tests.TEST_TIMEOUT == 60

    def test_default_debounce_is_int(self):
        """Test that DEBOUNCE_SECONDS has correct default value."""
        assert run_tests.DEBOUNCE_SECONDS == 5


class TestToolFiltering:
    """Test that only Edit and Write tools trigger tests."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        """Setup configuration for each test via patching."""
        self.patches = [
            patch.object(run_tests, "TEST_ENABLED", True),
            patch.object(run_tests, "TEST_COMMAND", "echo test"),
            patch.object(run_tests, "DEBOUNCE_SECONDS", 0),
        ]
        for p in self.patches:
            p.start()
        yield
        for p in self.patches:
            p.stop()

    def test_edit_tool_triggers(self):
        """Test that Edit tool triggers test execution."""
        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "test.py"},
            "cwd": "/tmp"
        }

        mock_logger = MagicMock()
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch.object(run_tests, "run_tests_background") as mock_run:
                with patch.object(run_tests, "get_log_dir") as mock_log_dir:
                    mock_log_dir.return_value = Path("/tmp/.claude/logs")
                    with patch.object(run_tests, "acquire_lock", return_value=123):
                        with patch.object(run_tests, "release_lock"):
                            with patch.object(run_tests, "update_last_run"):
                                with patch.object(run_tests, "get_plugin_logger", return_value=mock_logger):
                                    result = run_tests.main()

                assert result == 0
                mock_run.assert_called_once()

    def test_write_tool_triggers(self):
        """Test that Write tool triggers test execution."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": "test.py"},
            "cwd": "/tmp"
        }

        mock_logger = MagicMock()
        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch.object(run_tests, "run_tests_background") as mock_run:
                with patch.object(run_tests, "get_log_dir") as mock_log_dir:
                    mock_log_dir.return_value = Path("/tmp/.claude/logs")
                    with patch.object(run_tests, "acquire_lock", return_value=123):
                        with patch.object(run_tests, "release_lock"):
                            with patch.object(run_tests, "update_last_run"):
                                with patch.object(run_tests, "get_plugin_logger", return_value=mock_logger):
                                    result = run_tests.main()

                assert result == 0
                mock_run.assert_called_once()

    def test_read_tool_does_not_trigger(self):
        """Test that Read tool does not trigger test execution."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "test.py"},
            "cwd": "/tmp"
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch.object(run_tests, "run_tests_background") as mock_run:
                result = run_tests.main()

        assert result == 0
        mock_run.assert_not_called()

    def test_bash_tool_does_not_trigger(self):
        """Test that Bash tool does not trigger test execution."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "cwd": "/tmp"
        }

        with patch("sys.stdin", StringIO(json.dumps(input_data))):
            with patch.object(run_tests, "run_tests_background") as mock_run:
                result = run_tests.main()

        assert result == 0
        mock_run.assert_not_called()


class TestDebouncing:
    """Test that debouncing prevents rapid re-runs."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        """Setup configuration for each test via patching."""
        self.patches = [
            patch.object(run_tests, "TEST_ENABLED", True),
            patch.object(run_tests, "TEST_COMMAND", "echo test"),
            patch.object(run_tests, "DEBOUNCE_SECONDS", 5),
        ]
        for p in self.patches:
            p.start()
        yield
        for p in self.patches:
            p.stop()

    def test_debounce_prevents_immediate_rerun(self):
        """Test that recent run prevents immediate re-execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            # Simulate a recent run
            last_run_file = log_dir / ".last_run"
            last_run_file.write_text(str(time.time()))

            result = run_tests.should_debounce(log_dir)
            assert result is True

    def test_no_debounce_after_timeout(self):
        """Test that old runs allow re-execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            # Simulate an old run (10 seconds ago)
            last_run_file = log_dir / ".last_run"
            last_run_file.write_text(str(time.time() - 10))

            result = run_tests.should_debounce(log_dir)
            assert result is False

    def test_no_debounce_without_last_run_file(self):
        """Test that missing last_run file allows execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            result = run_tests.should_debounce(log_dir)
            assert result is False

    def test_debounce_handles_corrupted_file(self):
        """Test that corrupted last_run file allows execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            # Create corrupted file
            last_run_file = log_dir / ".last_run"
            last_run_file.write_text("invalid")

            result = run_tests.should_debounce(log_dir)
            assert result is False


class TestLogging:
    """Test logging functionality."""

    def test_get_log_dir_creates_directory(self):
        """Test that get_log_dir creates the log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = run_tests.get_log_dir(tmpdir)

            assert log_dir.exists()
            assert log_dir.is_dir()
            assert log_dir == Path(tmpdir) / ".claude" / "logs"

    def test_logger_creates_jsonl_output(self):
        """Test that get_plugin_logger creates JSONL formatted log entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            # Reset the global logger before test
            run_tests._logger = None
            logger = run_tests.get_plugin_logger(log_dir)

            logger.info("Test message 1", extra={"event": "test_event"})
            logger.info("Test message 2", extra={"event": "test_event"})
            # Flush handlers
            for handler in logger.handlers:
                handler.flush()

            log_file = log_dir / "test-runner.jsonl"
            assert log_file.exists()

            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 2

            # Verify JSONL format
            import json
            record1 = json.loads(lines[0])
            record2 = json.loads(lines[1])
            assert record1["message"] == "Test message 1"
            assert record2["message"] == "Test message 2"
            assert record1["plugin"] == "test-runner"
            # Check timestamp format (ISO format includes 'T' separator)
            assert "T" in record1["timestamp"]

    def test_update_last_run_writes_timestamp(self):
        """Test that update_last_run writes current timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            before = time.time()
            run_tests.update_last_run(log_dir)
            after = time.time()

            last_run_file = log_dir / ".last_run"
            assert last_run_file.exists()

            timestamp = float(last_run_file.read_text().strip())
            assert before <= timestamp <= after


class TestLocking:
    """Test lock acquisition and release."""

    def test_acquire_lock_succeeds(self):
        """Test that lock can be acquired."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = Path(tmpdir) / ".lock"

            fd = run_tests.acquire_lock(lock_file)

            assert fd is not None
            assert isinstance(fd, int)

            # Clean up
            run_tests.release_lock(fd)

    def test_acquire_lock_fails_when_locked(self):
        """Test that lock acquisition fails when already locked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = Path(tmpdir) / ".lock"

            fd1 = run_tests.acquire_lock(lock_file)
            assert fd1 is not None

            # Try to acquire again
            fd2 = run_tests.acquire_lock(lock_file)
            assert fd2 is None

            # Clean up
            run_tests.release_lock(fd1)

    def test_release_lock_allows_reacquisition(self):
        """Test that releasing lock allows reacquisition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = Path(tmpdir) / ".lock"

            fd1 = run_tests.acquire_lock(lock_file)
            assert fd1 is not None

            run_tests.release_lock(fd1)

            # Should be able to acquire again
            fd2 = run_tests.acquire_lock(lock_file)
            assert fd2 is not None

            # Clean up
            run_tests.release_lock(fd2)


class TestBackgroundExecution:
    """Test background test execution."""

    def test_run_tests_background_uses_shell(self):
        """Test that run_tests_background uses shell=True for command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            mock_logger = MagicMock()

            # Mock os.fork to prevent actual forking in tests
            with patch("os.fork", return_value=1):  # Parent process
                run_tests.run_tests_background("echo test", tmpdir, log_dir, mock_logger)

            # Parent should return immediately, no subprocess called
            # This test just ensures the function signature is correct


class TestInvalidInput:
    """Test handling of invalid input."""

    def test_invalid_json_returns_error(self):
        """Test that invalid JSON input returns error code."""
        with patch.object(run_tests, "TEST_ENABLED", True):
            with patch.object(run_tests, "TEST_COMMAND", "echo test"):
                with patch("sys.stdin", StringIO("invalid json")):
                    result = run_tests.main()

        assert result == 1

    def test_empty_file_path_handled(self):
        """Test that empty file_path is handled gracefully."""
        input_data = {
            "tool_name": "Edit",
            "tool_input": {},  # No file_path
            "cwd": "/tmp"
        }

        mock_logger = MagicMock()
        with patch.object(run_tests, "TEST_ENABLED", True):
            with patch.object(run_tests, "TEST_COMMAND", "echo test"):
                with patch.object(run_tests, "DEBOUNCE_SECONDS", 0):
                    with patch("sys.stdin", StringIO(json.dumps(input_data))):
                        with patch.object(run_tests, "run_tests_background") as mock_run:
                            with patch.object(run_tests, "get_log_dir") as mock_log_dir:
                                mock_log_dir.return_value = Path("/tmp/.claude/logs")
                                with patch.object(run_tests, "acquire_lock", return_value=123):
                                    with patch.object(run_tests, "release_lock"):
                                        with patch.object(run_tests, "update_last_run"):
                                            with patch.object(run_tests, "get_plugin_logger", return_value=mock_logger):
                                                result = run_tests.main()

        # Should still run (file_path is logged but not required)
        assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
