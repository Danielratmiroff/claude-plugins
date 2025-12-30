#!/usr/bin/env python3
"""
Comprehensive tests for Claude Code Observability System.
Tests both the observability hook and the dashboard components.
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "hooks"))
sys.path.insert(0, str(Path(__file__).parent))

import observability_hook
from dashboard import EventStore, LogWatcher, get_tool_color, build_events_table, build_stats_panel


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True)
    return log_dir


@pytest.fixture
def temp_log_file(temp_log_dir):
    """Create a temporary log file."""
    return temp_log_dir / "observability.jsonl"


@pytest.fixture
def sample_pre_tool_event():
    """Sample PreToolUse event data."""
    return {
        "hook_event_name": "PreToolUse",
        "session_id": "test-session-123",
        "tool_use_id": "tool-456",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "cwd": "/home/user/project"
    }


@pytest.fixture
def sample_post_tool_event():
    """Sample PostToolUse event data."""
    return {
        "hook_event_name": "PostToolUse",
        "session_id": "test-session-123",
        "tool_use_id": "tool-456",
        "tool_name": "Read",
        "tool_input": {"file_path": "/path/to/file.py"},
        "tool_response": {"success": True},
        "cwd": "/home/user/project"
    }


@pytest.fixture
def sample_events_jsonl(temp_log_file):
    """Create a log file with sample events."""
    events = [
        {
            "event_id": "abc123",
            "timestamp": "2024-01-15T10:30:00+00:00",
            "event_type": "PreToolUse",
            "session_id": "sess-1",
            "tool_use_id": "tool-1",
            "cwd": "/home/user",
            "tool": {"tool_name": "Bash", "command": "ls"},
            "hook_processing_ms": 1.5
        },
        {
            "event_id": "def456",
            "timestamp": "2024-01-15T10:30:01+00:00",
            "event_type": "PostToolUse",
            "session_id": "sess-1",
            "tool_use_id": "tool-1",
            "cwd": "/home/user",
            "tool": {"tool_name": "Bash", "command": "ls"},
            "response": {"success": True},
            "hook_processing_ms": 1.2
        },
        {
            "event_id": "ghi789",
            "timestamp": "2024-01-15T10:30:02+00:00",
            "event_type": "PreToolUse",
            "session_id": "sess-1",
            "tool_use_id": "tool-2",
            "cwd": "/home/user",
            "tool": {"tool_name": "Read", "file_path": "/test.py"},
            "hook_processing_ms": 0.8
        }
    ]
    with open(temp_log_file, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
    return temp_log_file


# ============================================================================
# Tests for observability_hook.py
# ============================================================================

class TestTruncateLargeValues:
    """Tests for the truncate_large_values function."""

    def test_truncate_short_string(self):
        """Short strings should not be truncated."""
        result = observability_hook.truncate_large_values("short", max_length=100)
        assert result == "short"

    def test_truncate_long_string(self):
        """Long strings should be truncated with indicator."""
        long_str = "x" * 2000
        result = observability_hook.truncate_large_values(long_str, max_length=100)
        assert len(result) < len(long_str)
        assert "[truncated]" in result
        assert result.startswith("x" * 100)

    def test_truncate_dict_values(self):
        """Dict values should be recursively truncated."""
        data = {"key": "x" * 200, "nested": {"inner": "y" * 200}}
        result = observability_hook.truncate_large_values(data, max_length=50)
        assert "[truncated]" in result["key"]
        assert "[truncated]" in result["nested"]["inner"]

    def test_truncate_list_values(self):
        """List values should be recursively truncated."""
        data = ["x" * 200, "y" * 200]
        result = observability_hook.truncate_large_values(data, max_length=50)
        assert "[truncated]" in result[0]
        assert "[truncated]" in result[1]

    def test_truncate_non_string_unchanged(self):
        """Non-string values should pass through unchanged."""
        assert observability_hook.truncate_large_values(123) == 123
        assert observability_hook.truncate_large_values(None) is None
        assert observability_hook.truncate_large_values(True) is True


class TestExtractToolMetadata:
    """Tests for the extract_tool_metadata function."""

    def test_extract_bash_metadata(self):
        """Bash tool should extract command."""
        data = {"tool_name": "Bash", "tool_input": {"command": "ls -la /very/long/path" * 20}}
        result = observability_hook.extract_tool_metadata(data)
        assert result["tool_name"] == "Bash"
        assert result["command"][:200] == ("ls -la /very/long/path" * 20)[:200]
        assert len(result["command"]) <= 200

    def test_extract_read_metadata(self):
        """Read tool should extract file_path."""
        data = {"tool_name": "Read", "tool_input": {"file_path": "/path/to/file.py"}}
        result = observability_hook.extract_tool_metadata(data)
        assert result["tool_name"] == "Read"
        assert result["file_path"] == "/path/to/file.py"

    def test_extract_write_metadata(self):
        """Write tool should extract file_path."""
        data = {"tool_name": "Write", "tool_input": {"file_path": "/path/to/output.txt"}}
        result = observability_hook.extract_tool_metadata(data)
        assert result["tool_name"] == "Write"
        assert result["file_path"] == "/path/to/output.txt"

    def test_extract_edit_metadata(self):
        """Edit tool should extract file_path."""
        data = {"tool_name": "Edit", "tool_input": {"file_path": "/path/to/edit.py"}}
        result = observability_hook.extract_tool_metadata(data)
        assert result["tool_name"] == "Edit"
        assert result["file_path"] == "/path/to/edit.py"

    def test_extract_grep_metadata(self):
        """Grep tool should extract pattern."""
        data = {"tool_name": "Grep", "tool_input": {"pattern": "function\\s+\\w+"}}
        result = observability_hook.extract_tool_metadata(data)
        assert result["tool_name"] == "Grep"
        assert result["pattern"] == "function\\s+\\w+"

    def test_extract_glob_metadata(self):
        """Glob tool should extract pattern."""
        data = {"tool_name": "Glob", "tool_input": {"pattern": "**/*.py"}}
        result = observability_hook.extract_tool_metadata(data)
        assert result["tool_name"] == "Glob"
        assert result["pattern"] == "**/*.py"

    def test_extract_webfetch_metadata(self):
        """WebFetch tool should extract url."""
        data = {"tool_name": "WebFetch", "tool_input": {"url": "https://example.com"}}
        result = observability_hook.extract_tool_metadata(data)
        assert result["tool_name"] == "WebFetch"
        assert result["url"] == "https://example.com"

    def test_extract_websearch_metadata(self):
        """WebSearch tool should extract query."""
        data = {"tool_name": "WebSearch", "tool_input": {"query": "python tutorials"}}
        result = observability_hook.extract_tool_metadata(data)
        assert result["tool_name"] == "WebSearch"
        assert result["query"] == "python tutorials"

    def test_extract_unknown_tool_metadata(self):
        """Unknown tools should have minimal metadata."""
        data = {"tool_name": "UnknownTool", "tool_input": {"foo": "bar"}}
        result = observability_hook.extract_tool_metadata(data)
        assert result == {"tool_name": "UnknownTool"}

    def test_extract_missing_tool_name(self):
        """Missing tool_name should default to 'unknown'."""
        data = {"tool_input": {"command": "ls"}}
        result = observability_hook.extract_tool_metadata(data)
        assert result["tool_name"] == "unknown"


class TestBuildEvent:
    """Tests for the build_event function."""

    def test_build_pre_tool_event(self, sample_pre_tool_event):
        """PreToolUse events should have correct structure."""
        start_time = time.time()
        event = observability_hook.build_event(sample_pre_tool_event, start_time)

        assert "event_id" in event
        assert len(event["event_id"]) == 16
        assert "timestamp" in event
        assert event["event_type"] == "PreToolUse"
        assert event["session_id"] == "test-session-123"
        assert event["tool_use_id"] == "tool-456"
        assert event["cwd"] == "/home/user/project"
        assert event["tool"]["tool_name"] == "Bash"
        assert "hook_processing_ms" in event
        assert "response" not in event

    def test_build_post_tool_event(self, sample_post_tool_event):
        """PostToolUse events should include response info."""
        start_time = time.time()
        event = observability_hook.build_event(sample_post_tool_event, start_time)

        assert event["event_type"] == "PostToolUse"
        assert "response" in event
        assert event["response"]["success"] is True

    def test_build_event_failed_response(self):
        """Failed responses should be captured."""
        data = {
            "hook_event_name": "PostToolUse",
            "session_id": "sess",
            "tool_use_id": "tool",
            "tool_name": "Bash",
            "tool_input": {},
            "tool_response": {"success": False}
        }
        event = observability_hook.build_event(data, time.time())
        assert event["response"]["success"] is False

    def test_event_id_uniqueness(self, sample_pre_tool_event):
        """Each event should have a unique ID."""
        ids = set()
        for _ in range(100):
            event = observability_hook.build_event(sample_pre_tool_event, time.time())
            ids.add(event["event_id"])
        assert len(ids) == 100

    def test_timestamp_format(self, sample_pre_tool_event):
        """Timestamp should be ISO format with timezone."""
        event = observability_hook.build_event(sample_pre_tool_event, time.time())
        # Should be parseable as ISO format
        datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))


class TestEnsureLogDir:
    """Tests for ensure_log_dir function."""

    def test_creates_log_directory(self, tmp_path):
        """Should create log directory if it doesn't exist."""
        with patch.object(observability_hook, 'LOG_DIR', tmp_path / "new_logs"):
            observability_hook.ensure_log_dir()
            assert observability_hook.LOG_DIR.exists()


class TestRotateLogIfNeeded:
    """Tests for log rotation functionality."""

    def test_no_rotation_under_limit(self, temp_log_file):
        """Should not rotate if under size limit."""
        temp_log_file.write_text("small content")
        with patch.object(observability_hook, 'LOG_FILE', temp_log_file):
            with patch.object(observability_hook, 'MAX_LOG_SIZE_MB', 50):
                observability_hook.rotate_log_if_needed()
        assert temp_log_file.exists()

    def test_rotation_over_limit(self, temp_log_file):
        """Should rotate if over size limit."""
        # Write ~2MB of data
        temp_log_file.write_text("x" * (2 * 1024 * 1024))
        with patch.object(observability_hook, 'LOG_FILE', temp_log_file):
            with patch.object(observability_hook, 'MAX_LOG_SIZE_MB', 1):
                observability_hook.rotate_log_if_needed()
        # Original file should be renamed
        assert not temp_log_file.exists()
        # Should find rotated file
        rotated_files = list(temp_log_file.parent.glob("*.jsonl"))
        assert len(rotated_files) == 1


class TestMainFunction:
    """Tests for the main function of observability_hook."""

    def test_main_with_valid_input(self, temp_log_dir, sample_pre_tool_event):
        """Main should log valid events."""
        log_file = temp_log_dir / "observability.jsonl"

        with patch.object(observability_hook, 'LOG_DIR', temp_log_dir):
            with patch.object(observability_hook, 'LOG_FILE', log_file):
                with patch('sys.stdin', StringIO(json.dumps(sample_pre_tool_event))):
                    with pytest.raises(SystemExit) as exc_info:
                        observability_hook.main()
                    assert exc_info.value.code == 0

        assert log_file.exists()
        with open(log_file) as f:
            logged = json.loads(f.read().strip())
        assert logged["event_type"] == "PreToolUse"

    def test_main_with_invalid_json(self):
        """Invalid JSON should exit silently with 0."""
        with patch('sys.stdin', StringIO("not valid json")):
            with pytest.raises(SystemExit) as exc_info:
                observability_hook.main()
            assert exc_info.value.code == 0

    def test_main_with_empty_input(self):
        """Empty input should exit silently with 0."""
        with patch('sys.stdin', StringIO("")):
            with pytest.raises(SystemExit) as exc_info:
                observability_hook.main()
            assert exc_info.value.code == 0


# ============================================================================
# Tests for dashboard.py
# ============================================================================

class TestEventStore:
    """Tests for the EventStore class."""

    def test_add_single_event(self):
        """Should add and track a single event."""
        store = EventStore()
        event = {"tool": {"tool_name": "Bash"}, "event_type": "PreToolUse"}
        store.add_event(event)

        assert len(store.events) == 1
        assert store.tool_counts["Bash"] == 1

    def test_add_multiple_events(self):
        """Should track multiple events by tool."""
        store = EventStore()
        store.add_event({"tool": {"tool_name": "Bash"}, "event_type": "PreToolUse"})
        store.add_event({"tool": {"tool_name": "Read"}, "event_type": "PreToolUse"})
        store.add_event({"tool": {"tool_name": "Bash"}, "event_type": "PreToolUse"})

        assert len(store.events) == 3
        assert store.tool_counts["Bash"] == 2
        assert store.tool_counts["Read"] == 1

    def test_max_events_limit(self):
        """Should cap events at max_events."""
        store = EventStore(max_events=5)
        for i in range(10):
            store.add_event({"tool": {"tool_name": "Bash"}, "event_type": "PreToolUse"})

        assert len(store.events) == 5
        assert store.tool_counts["Bash"] == 10  # Counts still track all

    def test_success_count(self):
        """Should track successful PostToolUse events."""
        store = EventStore()
        store.add_event({"tool": {"tool_name": "Bash"}, "event_type": "PostToolUse", "response": {"success": True}})
        store.add_event({"tool": {"tool_name": "Bash"}, "event_type": "PostToolUse", "response": {"success": True}})

        assert store.success_count == 2
        assert store.error_count == 0

    def test_error_count(self):
        """Should track failed PostToolUse events."""
        store = EventStore()
        store.add_event({"tool": {"tool_name": "Bash"}, "event_type": "PostToolUse", "response": {"success": False}})

        assert store.success_count == 0
        assert store.error_count == 1

    def test_pre_tool_use_no_count(self):
        """PreToolUse events should not affect success/error counts."""
        store = EventStore()
        store.add_event({"tool": {"tool_name": "Bash"}, "event_type": "PreToolUse"})

        assert store.success_count == 0
        assert store.error_count == 0


class TestLogWatcher:
    """Tests for the LogWatcher class."""

    def test_get_new_events_empty_file(self, temp_log_file):
        """Should return empty list for empty/nonexistent file."""
        watcher = LogWatcher(temp_log_file)
        events = watcher.get_new_events()
        assert events == []

    def test_get_new_events_reads_all(self, sample_events_jsonl):
        """Should read all events on first call."""
        watcher = LogWatcher(sample_events_jsonl)
        events = watcher.get_new_events()
        assert len(events) == 3

    def test_get_new_events_incremental(self, temp_log_file):
        """Should only return new events on subsequent calls."""
        # Write initial events
        with open(temp_log_file, "w") as f:
            f.write(json.dumps({"event_id": "1"}) + "\n")
            f.write(json.dumps({"event_id": "2"}) + "\n")

        watcher = LogWatcher(temp_log_file)
        events = watcher.get_new_events()
        assert len(events) == 2

        # Add more events
        with open(temp_log_file, "a") as f:
            f.write(json.dumps({"event_id": "3"}) + "\n")

        events = watcher.get_new_events()
        assert len(events) == 1
        assert events[0]["event_id"] == "3"

    def test_get_new_events_skips_invalid_json(self, temp_log_file):
        """Should skip invalid JSON lines."""
        with open(temp_log_file, "w") as f:
            f.write(json.dumps({"event_id": "1"}) + "\n")
            f.write("not valid json\n")
            f.write(json.dumps({"event_id": "2"}) + "\n")

        watcher = LogWatcher(temp_log_file)
        events = watcher.get_new_events()
        assert len(events) == 2

    def test_get_new_events_nonexistent_file(self, tmp_path):
        """Should handle nonexistent file gracefully."""
        watcher = LogWatcher(tmp_path / "nonexistent.jsonl")
        events = watcher.get_new_events()
        assert events == []


class TestGetToolColor:
    """Tests for the get_tool_color function."""

    def test_known_tools_have_colors(self):
        """Known tools should have specific colors."""
        assert get_tool_color("Bash") == "red"
        assert get_tool_color("Read") == "blue"
        assert get_tool_color("Write") == "green"
        assert get_tool_color("Edit") == "yellow"
        assert get_tool_color("Grep") == "cyan"
        assert get_tool_color("Glob") == "magenta"

    def test_unknown_tools_are_white(self):
        """Unknown tools should be white."""
        assert get_tool_color("UnknownTool") == "white"
        assert get_tool_color("WebFetch") == "white"


class TestBuildEventsTable:
    """Tests for the build_events_table function."""

    def test_build_table_with_events(self):
        """Should build a table with event data."""
        events = [
            {
                "timestamp": "2024-01-15T10:30:00+00:00",
                "event_type": "PreToolUse",
                "session_id": "test-session-123",
                "tool": {"tool_name": "Bash", "command": "ls -la"}
            }
        ]
        table = build_events_table(events)
        assert table.title == "Recent Events"
        assert len(table.columns) == 5

    def test_build_table_empty_events(self):
        """Should build empty table with no events."""
        table = build_events_table([])
        assert table.title == "Recent Events"

    def test_build_table_limits_to_15(self):
        """Should only show last 15 events."""
        events = [
            {
                "timestamp": f"2024-01-15T10:{i:02d}:00+00:00",
                "event_type": "PreToolUse",
                "tool": {"tool_name": "Bash", "command": f"cmd{i}"}
            }
            for i in range(20)
        ]
        table = build_events_table(events)
        assert table.row_count == 15


class TestBuildStatsPanel:
    """Tests for the build_stats_panel function."""

    def test_build_stats_empty_store(self):
        """Should build panel with zero counts."""
        store = EventStore()
        panel = build_stats_panel(store)
        assert panel.title == "Stats"

    def test_build_stats_with_data(self):
        """Should show tool counts in panel."""
        store = EventStore()
        for _ in range(5):
            store.add_event({"tool": {"tool_name": "Bash"}, "event_type": "PreToolUse"})
        for _ in range(3):
            store.add_event({"tool": {"tool_name": "Read"}, "event_type": "PostToolUse", "response": {"success": True}})

        panel = build_stats_panel(store)
        assert panel.title == "Stats"


# ============================================================================
# Integration Tests
# ============================================================================

class TestObservabilityIntegration:
    """Integration tests for the full observability pipeline."""

    def test_hook_logs_then_dashboard_reads(self, temp_log_dir, sample_pre_tool_event, sample_post_tool_event):
        """Dashboard should read events logged by the hook."""
        log_file = temp_log_dir / "observability.jsonl"

        # Simulate hook logging events
        with patch.object(observability_hook, 'LOG_DIR', temp_log_dir):
            with patch.object(observability_hook, 'LOG_FILE', log_file):
                with patch('sys.stdin', StringIO(json.dumps(sample_pre_tool_event))):
                    with pytest.raises(SystemExit):
                        observability_hook.main()

                with patch('sys.stdin', StringIO(json.dumps(sample_post_tool_event))):
                    with pytest.raises(SystemExit):
                        observability_hook.main()

        # Dashboard reads events
        watcher = LogWatcher(log_file)
        events = watcher.get_new_events()

        assert len(events) == 2
        assert events[0]["event_type"] == "PreToolUse"
        assert events[1]["event_type"] == "PostToolUse"

    def test_event_store_processes_hook_output(self, temp_log_dir, sample_post_tool_event):
        """EventStore should correctly process hook output."""
        log_file = temp_log_dir / "observability.jsonl"

        with patch.object(observability_hook, 'LOG_DIR', temp_log_dir):
            with patch.object(observability_hook, 'LOG_FILE', log_file):
                with patch('sys.stdin', StringIO(json.dumps(sample_post_tool_event))):
                    with pytest.raises(SystemExit):
                        observability_hook.main()

        watcher = LogWatcher(log_file)
        store = EventStore()
        for event in watcher.get_new_events():
            store.add_event(event)

        assert store.success_count == 1
        assert store.tool_counts["Read"] == 1


class TestEdgeCases:
    """Edge case tests."""

    def test_hook_handles_empty_tool_input(self, temp_log_dir):
        """Hook should handle events with empty tool_input."""
        log_file = temp_log_dir / "observability.jsonl"
        data = {
            "hook_event_name": "PreToolUse",
            "session_id": "sess",
            "tool_use_id": "tool",
            "tool_name": "Bash",
            "tool_input": {},
            "cwd": "/home"
        }

        with patch.object(observability_hook, 'LOG_DIR', temp_log_dir):
            with patch.object(observability_hook, 'LOG_FILE', log_file):
                with patch('sys.stdin', StringIO(json.dumps(data))):
                    with pytest.raises(SystemExit) as exc_info:
                        observability_hook.main()
                    assert exc_info.value.code == 0

    def test_hook_handles_unicode(self, temp_log_dir):
        """Hook should handle unicode characters."""
        log_file = temp_log_dir / "observability.jsonl"
        data = {
            "hook_event_name": "PreToolUse",
            "session_id": "sess",
            "tool_use_id": "tool",
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'Hello \u4e16\u754c \ud83c\udf0d'"},
            "cwd": "/home"
        }

        with patch.object(observability_hook, 'LOG_DIR', temp_log_dir):
            with patch.object(observability_hook, 'LOG_FILE', log_file):
                with patch('sys.stdin', StringIO(json.dumps(data))):
                    with pytest.raises(SystemExit) as exc_info:
                        observability_hook.main()
                    assert exc_info.value.code == 0

        with open(log_file) as f:
            logged = json.loads(f.read().strip())
        assert "Hello" in logged["tool"]["command"]

    def test_dashboard_handles_malformed_event(self):
        """Dashboard should handle malformed events gracefully."""
        store = EventStore()
        # Missing expected fields
        store.add_event({})
        assert store.tool_counts["unknown"] == 1

    def test_log_watcher_handles_concurrent_writes(self, temp_log_file):
        """LogWatcher should handle file growing during read."""
        # Write initial data
        with open(temp_log_file, "w") as f:
            f.write(json.dumps({"event_id": "1"}) + "\n")

        watcher = LogWatcher(temp_log_file)
        events = watcher.get_new_events()
        assert len(events) == 1

        # Simulate another process writing
        with open(temp_log_file, "a") as f:
            for i in range(100):
                f.write(json.dumps({"event_id": str(i + 2)}) + "\n")

        events = watcher.get_new_events()
        assert len(events) == 100


class TestPerformance:
    """Performance-related tests."""

    def test_truncate_handles_deeply_nested(self):
        """Truncation should handle deeply nested structures."""
        data = {"level": 0}
        current = data
        for i in range(50):
            current["nested"] = {"level": i + 1, "data": "x" * 100}
            current = current["nested"]

        result = observability_hook.truncate_large_values(data, max_length=50)
        assert "level" in result

    def test_event_store_max_events_memory(self):
        """EventStore should properly limit memory usage."""
        store = EventStore(max_events=100)
        for i in range(1000):
            store.add_event({
                "tool": {"tool_name": "Bash"},
                "event_type": "PreToolUse",
                "large_data": "x" * 1000
            })

        assert len(store.events) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
