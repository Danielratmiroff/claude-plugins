import pytest
import json
import sys
import os
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/notifications/scripts'))

from notify_action_required import get_notification_title, get_notification_urgency, main


class TestGetNotificationTitle:
    def test_permission_prompt(self):
        assert get_notification_title("permission_prompt") == "Claude Code - Permission Required"

    def test_idle_prompt(self):
        assert get_notification_title("idle_prompt") == "Claude Code - Awaiting Input"

    def test_unknown(self):
        assert get_notification_title("unknown") == "Claude Code - Action Required"


class TestGetNotificationUrgency:
    def test_permission_prompt_is_critical(self):
        assert get_notification_urgency("permission_prompt") == "critical"

    def test_idle_prompt_is_normal(self):
        assert get_notification_urgency("idle_prompt") == "normal"

    def test_unknown_is_normal(self):
        assert get_notification_urgency("unknown") == "normal"


class TestMain:
    @patch("notify_action_required.play_sound")
    @patch("notify_action_required.send_notification")
    def test_main_with_permission_prompt(self, mock_notify, mock_sound):
        data = {"notification_type": "permission_prompt", "message": "Allow file write?"}
        with patch("sys.stdin", StringIO(json.dumps(data))):
            result = main()
        assert result == 0
        mock_notify.assert_called_once_with(
            "Claude Code - Permission Required",
            "Allow file write?",
            "critical"
        )
        mock_sound.assert_called_once_with("attention")

    @patch("notify_action_required.play_sound")
    @patch("notify_action_required.send_notification")
    def test_main_with_empty_stdin(self, mock_notify, mock_sound):
        with patch("sys.stdin", StringIO("")):
            result = main()
        assert result == 0
        mock_notify.assert_called_once()
        assert "Action Required" in mock_notify.call_args[0][0]
