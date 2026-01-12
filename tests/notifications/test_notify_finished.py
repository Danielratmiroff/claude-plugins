import pytest
import json
import sys
import os
from unittest.mock import patch, MagicMock
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/notifications/scripts'))

from notify_finished import format_duration, format_cost, build_notification_body, main


class TestFormatDuration:
    def test_milliseconds(self):
        assert format_duration(500) == "500ms"

    def test_seconds(self):
        assert format_duration(5000) == "5.0s"

    def test_minutes(self):
        assert format_duration(125000) == "2m 5s"


class TestFormatCost:
    def test_small_cost(self):
        assert format_cost(0.0012) == "$0.0012"

    def test_normal_cost(self):
        assert format_cost(1.23) == "$1.23"


class TestBuildNotificationBody:
    def test_full_data(self):
        data = {
            "stop_hook_data": {
                "stop_reason": "end_turn",
                "duration_ms": 5000,
                "num_turns": 3,
                "total_cost_usd": 0.05,
                "total_input_tokens": 1000,
                "total_output_tokens": 500
            }
        }
        body = build_notification_body(data)
        assert "Completed" in body
        assert "5.0s" in body
        assert "3" in body
        assert "$0.05" in body
        assert "1,000" in body
        assert "500" in body

    def test_empty_data(self):
        body = build_notification_body({})
        assert "Completed" in body


class TestMain:
    @patch("notify_finished.play_sound")
    @patch("notify_finished.send_notification")
    def test_main_with_data(self, mock_notify, mock_sound):
        data = {"stop_hook_data": {"stop_reason": "end_turn", "duration_ms": 1000}}
        with patch("sys.stdin", StringIO(json.dumps(data))):
            result = main()
        assert result == 0
        mock_notify.assert_called_once()
        mock_sound.assert_called_once_with("complete")

    @patch("notify_finished.play_sound")
    @patch("notify_finished.send_notification")
    def test_main_with_empty_stdin(self, mock_notify, mock_sound):
        with patch("sys.stdin", StringIO("")):
            result = main()
        assert result == 0
        mock_notify.assert_called_once()
