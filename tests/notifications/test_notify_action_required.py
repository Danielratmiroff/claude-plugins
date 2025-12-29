#!/usr/bin/env python3
"""Tests for notify_action_required.py hook"""

import pytest
from unittest.mock import patch, MagicMock, call
from io import StringIO
import json
import sys
import os

# Import the module to test - navigate from tests/notifications/ to plugins/notifications/scripts/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'plugins', 'notifications', 'scripts'))
import notify_action_required


class TestNotificationTypeMapping:
    """Test urgency and title mapping functions."""

    def test_urgency_permission_prompt(self):
        """Permission prompts should have critical urgency."""
        assert notify_action_required.get_notification_urgency("permission_prompt") == "critical"

    def test_urgency_idle_prompt(self):
        """Idle prompts should have normal urgency."""
        assert notify_action_required.get_notification_urgency("idle_prompt") == "normal"

    def test_urgency_unknown_type(self):
        """Unknown types should default to normal urgency."""
        assert notify_action_required.get_notification_urgency("unknown_type") == "normal"

    def test_urgency_empty_string(self):
        """Empty string should default to normal urgency."""
        assert notify_action_required.get_notification_urgency("") == "normal"

    def test_title_permission_prompt(self):
        """Permission prompts should have specific title."""
        expected = "Claude Code - Permission Required"
        assert notify_action_required.get_notification_title("permission_prompt") == expected

    def test_title_idle_prompt(self):
        """Idle prompts should have specific title."""
        expected = "Claude Code - Awaiting Your Input"
        assert notify_action_required.get_notification_title("idle_prompt") == expected

    def test_title_unknown_type(self):
        """Unknown types should have default title."""
        expected = "Claude Code - Action Required"
        assert notify_action_required.get_notification_title("unknown_type") == expected

    def test_title_empty_string(self):
        """Empty string should have default title."""
        expected = "Claude Code - Action Required"
        assert notify_action_required.get_notification_title("") == expected


class TestReadStdin:
    """Test JSON parsing from stdin."""

    def test_read_valid_json(self):
        """Should parse valid JSON input."""
        test_input = '{"notification_type": "permission_prompt", "message": "Test"}'
        with patch('sys.stdin', StringIO(test_input)):
            result = notify_action_required.read_stdin()
            assert result == {"notification_type": "permission_prompt", "message": "Test"}

    def test_read_empty_input(self):
        """Should return None for empty input."""
        with patch('sys.stdin', StringIO("")):
            result = notify_action_required.read_stdin()
            assert result is None

    def test_read_whitespace_only(self):
        """Should return None for whitespace-only input."""
        with patch('sys.stdin', StringIO("   \n  \t  ")):
            result = notify_action_required.read_stdin()
            assert result is None

    def test_read_invalid_json(self):
        """Should return None for invalid JSON."""
        with patch('sys.stdin', StringIO("not valid json")):
            result = notify_action_required.read_stdin()
            assert result is None

    def test_read_complex_json(self):
        """Should parse complex JSON structures."""
        test_input = json.dumps({
            "notification_type": "idle_prompt",
            "message": "Test message",
            "extra_data": {"nested": "value"}
        })
        with patch('sys.stdin', StringIO(test_input)):
            result = notify_action_required.read_stdin()
            assert result["notification_type"] == "idle_prompt"
            assert result["message"] == "Test message"
            assert result["extra_data"]["nested"] == "value"


class TestSendNotification:
    """Test desktop notification sending."""

    @patch('subprocess.Popen')
    def test_send_notification_success(self, mock_popen):
        """Should successfully send notification."""
        result = notify_action_required.send_notification(
            "Test Title",
            "Test Body",
            "normal"
        )
        assert result is True
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "notify-send" in call_args
        assert "--app-name" in call_args
        assert "Claude Code" in call_args
        assert "--icon" in call_args
        assert "dialog-question" in call_args
        assert "--urgency" in call_args
        assert "normal" in call_args
        assert "Test Title" in call_args
        assert "Test Body" in call_args

    @patch('subprocess.Popen')
    def test_send_notification_critical_urgency(self, mock_popen):
        """Should send notification with critical urgency."""
        notify_action_required.send_notification(
            "Critical",
            "Urgent message",
            "critical"
        )
        call_args = mock_popen.call_args[0][0]
        assert "critical" in call_args

    @patch('subprocess.Popen', side_effect=Exception("Command failed"))
    def test_send_notification_failure(self, mock_popen):
        """Should handle notification failure gracefully."""
        result = notify_action_required.send_notification(
            "Test",
            "Body",
            "normal"
        )
        assert result is False


class TestSoundPlayback:
    """Test sound playback functionality."""

    @patch.dict(os.environ, {"CLAUDE_ACTION_SOUND": "0"})
    @patch('subprocess.Popen')
    def test_sound_disabled_by_env_var(self, mock_popen):
        """Should skip sound when disabled via environment variable."""
        # Reload module to pick up new env var
        import importlib
        importlib.reload(notify_action_required)
        result = notify_action_required.play_sound()
        assert result is True
        mock_popen.assert_not_called()

    @patch('os.path.exists', return_value=False)
    @patch('subprocess.Popen')
    def test_sound_file_missing(self, mock_popen, mock_exists):
        """Should handle missing sound file gracefully."""
        with patch.dict(os.environ, {"CLAUDE_ACTION_SOUND": "1"}):
            import importlib
            importlib.reload(notify_action_required)
            result = notify_action_required.play_sound()
            assert result is False
            mock_popen.assert_not_called()

    @patch('os.path.exists', return_value=True)
    @patch('subprocess.Popen')
    def test_sound_paplay_success(self, mock_popen, mock_exists):
        """Should use paplay for sound playback."""
        with patch.dict(os.environ, {"CLAUDE_ACTION_SOUND": "1"}):
            import importlib
            importlib.reload(notify_action_required)
            result = notify_action_required.play_sound()
            assert result is True
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert "paplay" in call_args

    @patch('os.path.exists', return_value=True)
    @patch('subprocess.Popen')
    def test_sound_paplay_fallback_to_aplay(self, mock_popen, mock_exists):
        """Should fallback to aplay if paplay fails."""
        # First call (paplay) raises exception, second call (aplay) succeeds
        mock_popen.side_effect = [Exception("paplay failed"), MagicMock()]
        with patch.dict(os.environ, {"CLAUDE_ACTION_SOUND": "1"}):
            import importlib
            importlib.reload(notify_action_required)
            result = notify_action_required.play_sound()
            assert result is True
            assert mock_popen.call_count == 2
            # Check that aplay was called second
            call_args = mock_popen.call_args[0][0]
            assert "aplay" in call_args

    @patch('os.path.exists', return_value=True)
    @patch('subprocess.Popen', side_effect=Exception("All failed"))
    def test_sound_all_players_fail(self, mock_popen, mock_exists):
        """Should handle all sound players failing."""
        with patch.dict(os.environ, {"CLAUDE_ACTION_SOUND": "1"}):
            import importlib
            importlib.reload(notify_action_required)
            result = notify_action_required.play_sound()
            assert result is False


class TestMainFunction:
    """Test main function integration."""

    @patch('notify_action_required.play_sound', return_value=True)
    @patch('notify_action_required.send_notification', return_value=True)
    def test_main_permission_prompt(self, mock_notify, mock_sound):
        """Should handle permission prompt correctly."""
        test_input = json.dumps({
            "notification_type": "permission_prompt",
            "message": "Claude needs permission to execute command"
        })
        with patch('sys.stdin', StringIO(test_input)):
            result = notify_action_required.main()
            assert result == 0
            mock_notify.assert_called_once_with(
                "Claude Code - Permission Required",
                "Claude needs permission to execute command",
                "critical"
            )
            mock_sound.assert_called_once()

    @patch('notify_action_required.play_sound', return_value=True)
    @patch('notify_action_required.send_notification', return_value=True)
    def test_main_idle_prompt(self, mock_notify, mock_sound):
        """Should handle idle prompt correctly."""
        test_input = json.dumps({
            "notification_type": "idle_prompt",
            "message": "Waiting for your response"
        })
        with patch('sys.stdin', StringIO(test_input)):
            result = notify_action_required.main()
            assert result == 0
            mock_notify.assert_called_once_with(
                "Claude Code - Awaiting Your Input",
                "Waiting for your response",
                "normal"
            )
            mock_sound.assert_called_once()

    @patch('notify_action_required.play_sound', return_value=True)
    @patch('notify_action_required.send_notification', return_value=True)
    def test_main_unknown_type(self, mock_notify, mock_sound):
        """Should handle unknown notification type with defaults."""
        test_input = json.dumps({
            "notification_type": "unknown_type",
            "message": "Some message"
        })
        with patch('sys.stdin', StringIO(test_input)):
            result = notify_action_required.main()
            assert result == 0
            mock_notify.assert_called_once_with(
                "Claude Code - Action Required",
                "Some message",
                "normal"
            )
            mock_sound.assert_called_once()

    @patch('notify_action_required.play_sound', return_value=True)
    @patch('notify_action_required.send_notification', return_value=True)
    def test_main_empty_input(self, mock_notify, mock_sound):
        """Should handle empty input with fallback notification."""
        with patch('sys.stdin', StringIO("")):
            result = notify_action_required.main()
            assert result == 0
            mock_notify.assert_called_once_with(
                "Claude Code - Action Required",
                "Claude needs your input",
                "normal"
            )
            mock_sound.assert_called_once()

    @patch('notify_action_required.play_sound', return_value=True)
    @patch('notify_action_required.send_notification', return_value=True)
    def test_main_missing_message_field(self, mock_notify, mock_sound):
        """Should use default message when message field is missing."""
        test_input = json.dumps({
            "notification_type": "permission_prompt"
        })
        with patch('sys.stdin', StringIO(test_input)):
            result = notify_action_required.main()
            assert result == 0
            mock_notify.assert_called_once_with(
                "Claude Code - Permission Required",
                "Claude needs your input",
                "critical"
            )
            mock_sound.assert_called_once()

    @patch('notify_action_required.play_sound', return_value=True)
    @patch('notify_action_required.send_notification', return_value=True)
    def test_main_missing_notification_type(self, mock_notify, mock_sound):
        """Should use defaults when notification_type is missing."""
        test_input = json.dumps({
            "message": "Test message"
        })
        with patch('sys.stdin', StringIO(test_input)):
            result = notify_action_required.main()
            assert result == 0
            mock_notify.assert_called_once_with(
                "Claude Code - Action Required",
                "Test message",
                "normal"
            )
            mock_sound.assert_called_once()

    @patch('notify_action_required.play_sound', return_value=True)
    @patch('notify_action_required.send_notification', return_value=False)
    def test_main_notification_fails(self, mock_notify, mock_sound):
        """Should still play sound even if notification fails."""
        test_input = json.dumps({
            "notification_type": "permission_prompt",
            "message": "Test"
        })
        with patch('sys.stdin', StringIO(test_input)):
            result = notify_action_required.main()
            assert result == 0
            mock_sound.assert_called_once()

    @patch('notify_action_required.play_sound', return_value=False)
    @patch('notify_action_required.send_notification', return_value=True)
    def test_main_sound_fails(self, mock_notify, mock_sound):
        """Should still return success even if sound fails."""
        test_input = json.dumps({
            "notification_type": "idle_prompt",
            "message": "Test"
        })
        with patch('sys.stdin', StringIO(test_input)):
            result = notify_action_required.main()
            assert result == 0
            mock_notify.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
