#!/usr/bin/env python3
"""
Tests for shared logging module.

Verifies that the JSONL logging produces correctly formatted output
with all required fields.
"""

import json
import logging
import sys
import tempfile
from pathlib import Path

import pytest

# Add the shared directory to the path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.logging import get_logger, log_event, PluginJsonFormatter


class TestGetLogger:
    """Test logger creation and configuration."""

    def test_creates_logger_with_plugin_name(self, tmp_path):
        """Logger should be created with plugin-specific name."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("test-plugin", log_file)

        assert logger.name == "claude-plugin.test-plugin"

    def test_creates_log_directory(self, tmp_path):
        """Logger should create parent directories if they don't exist."""
        log_file = tmp_path / "subdir" / "nested" / "test.jsonl"
        # Use unique name to avoid logger caching issues
        get_logger("dir-creation-test", log_file)

        assert log_file.parent.exists()

    def test_returns_same_logger_on_multiple_calls(self, tmp_path):
        """Calling get_logger multiple times should return the same instance."""
        log_file = tmp_path / "test.jsonl"
        logger1 = get_logger("same-plugin", log_file)
        logger2 = get_logger("same-plugin", log_file)

        assert logger1 is logger2
        # Should only have one handler
        assert len(logger1.handlers) == 1

    def test_sets_correct_log_level(self, tmp_path):
        """Logger should be configured with the specified level."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("level-test", log_file, level=logging.WARNING)

        assert logger.level == logging.WARNING


class TestJsonOutput:
    """Test JSON output format and required fields."""

    def test_output_is_valid_json(self, tmp_path):
        """Each log line should be valid JSON."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("json-test", log_file)

        logger.info("Test message")
        logger.handlers[0].flush()

        content = log_file.read_text().strip()
        # Should parse without error
        record = json.loads(content)
        assert isinstance(record, dict)

    def test_contains_required_fields(self, tmp_path):
        """Log entries should contain all required fields."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("fields-test", log_file)

        logger.info("Test message")
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())

        # Required fields per spec
        assert "timestamp" in record
        assert "level" in record
        assert "plugin" in record
        assert "message" in record

    def test_timestamp_is_iso8601(self, tmp_path):
        """Timestamp should be ISO 8601 format."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("timestamp-test", log_file)

        logger.info("Test message")
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())

        # ISO 8601 format should include 'T' separator and timezone info
        timestamp = record["timestamp"]
        assert "T" in timestamp
        # Should have timezone or Z suffix
        assert "+" in timestamp or "-" in timestamp or timestamp.endswith("Z")

    def test_level_field_values(self, tmp_path):
        """Level field should have correct values for each log level."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("level-values", log_file)

        logger.debug("debug msg")
        logger.info("info msg")
        logger.warning("warning msg")
        logger.error("error msg")
        logger.critical("critical msg")
        logger.handlers[0].flush()

        lines = log_file.read_text().strip().split("\n")
        records = [json.loads(line) for line in lines]

        levels = [r["level"] for r in records]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_plugin_field_added(self, tmp_path):
        """Plugin field should be added to every log entry."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("my-plugin", log_file)

        logger.info("Test message")
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())
        assert record["plugin"] == "my-plugin"

    def test_message_field_content(self, tmp_path):
        """Message field should contain the log message."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("message-test", log_file)

        logger.info("This is my test message")
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())
        assert record["message"] == "This is my test message"


class TestExtraFields:
    """Test extra/custom fields in log entries."""

    def test_event_field_from_extra(self, tmp_path):
        """Event field should be included when passed in extra."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("event-test", log_file)

        logger.info("Command blocked", extra={"event": "command_blocked"})
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())
        assert record["event"] == "command_blocked"

    def test_custom_fields_included(self, tmp_path):
        """Custom fields passed in extra should be included."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("custom-test", log_file)

        logger.warning(
            "Blocked command",
            extra={
                "event": "command_blocked",
                "command": "rm -rf /",
                "reasons": ["CRITICAL: Recursive deletion"],
            },
        )
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())
        assert record["command"] == "rm -rf /"
        assert record["reasons"] == ["CRITICAL: Recursive deletion"]

    def test_default_event_when_not_provided(self, tmp_path):
        """Event field should default to log level name when not provided."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("default-event", log_file)

        logger.info("No event provided")
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())
        assert record["event"] == "info"


class TestLogEvent:
    """Test the log_event convenience function."""

    def test_log_event_basic(self, tmp_path):
        """log_event should log with all standard fields."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("log-event-test", log_file)

        log_event(
            logger,
            logging.WARNING,
            "Blocked dangerous command",
            "command_blocked",
            command="rm -rf /",
        )
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())
        assert record["level"] == "WARNING"
        assert record["message"] == "Blocked dangerous command"
        assert record["event"] == "command_blocked"
        assert record["command"] == "rm -rf /"

    def test_log_event_with_multiple_kwargs(self, tmp_path):
        """log_event should handle multiple extra kwargs."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("kwargs-test", log_file)

        log_event(
            logger,
            logging.INFO,
            "Tool use logged",
            "post_tool_use",
            tool_name="Bash",
            session_id="abc123",
            duration_ms=150,
        )
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())
        assert record["tool_name"] == "Bash"
        assert record["session_id"] == "abc123"
        assert record["duration_ms"] == 150


class TestJSONLFormat:
    """Test JSONL (JSON Lines) format compliance."""

    def test_multiple_entries_one_per_line(self, tmp_path):
        """Each log entry should be on a single line."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("multiline-test", log_file)

        logger.info("First message")
        logger.info("Second message")
        logger.info("Third message")
        logger.handlers[0].flush()

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3

        # Each line should be valid JSON
        for line in lines:
            json.loads(line)

    def test_no_newlines_in_json(self, tmp_path):
        """JSON output should not contain newlines."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("newline-test", log_file)

        # Log a message with newlines
        logger.info("Message with\nnewlines\nin it")
        logger.handlers[0].flush()

        content = log_file.read_text()
        lines = content.strip().split("\n")

        # Should still be one line (newlines escaped in JSON)
        assert len(lines) == 1

    def test_special_characters_escaped(self, tmp_path):
        """Special characters should be properly JSON escaped."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("escape-test", log_file)

        logger.info('Message with "quotes" and \\ backslash')
        logger.handlers[0].flush()

        # Should parse without error
        record = json.loads(log_file.read_text().strip())
        assert '"quotes"' in record["message"]
        assert "\\" in record["message"]


class TestFileHandling:
    """Test file handling and append behavior."""

    def test_appends_to_existing_file(self, tmp_path):
        """New log entries should append to existing file."""
        log_file = tmp_path / "test.jsonl"

        # Create first logger and log
        logger1 = get_logger("append-test-1", log_file)
        logger1.info("First entry")
        logger1.handlers[0].flush()
        # Close the handler
        for handler in logger1.handlers[:]:
            handler.close()
            logger1.removeHandler(handler)

        # Create new logger with different name and log
        logger2 = get_logger("append-test-2", log_file)
        logger2.info("Second entry")
        logger2.handlers[0].flush()

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_handles_unicode(self, tmp_path):
        """Should handle Unicode characters correctly."""
        log_file = tmp_path / "test.jsonl"
        logger = get_logger("unicode-test", log_file)

        logger.info("Unicode: \u00e9\u00e8\u00ea \u4e2d\u6587 \U0001f604")
        logger.handlers[0].flush()

        record = json.loads(log_file.read_text().strip())
        assert "\u00e9" in record["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
