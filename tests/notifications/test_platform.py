import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/notifications/scripts'))

from platform_utils import detect_os, get_sound_path, send_notification, play_sound


class TestDetectOS:
    def test_linux(self):
        with patch("platform.system", return_value="Linux"):
            assert detect_os() == "linux"

    def test_macos(self):
        with patch("platform.system", return_value="Darwin"):
            assert detect_os() == "macos"

    def test_windows(self):
        with patch("platform.system", return_value="Windows"):
            assert detect_os() == "windows"

    def test_unknown_defaults_to_linux(self):
        with patch("platform.system", return_value="FreeBSD"):
            assert detect_os() == "linux"


class TestGetSoundPath:
    def test_linux_complete(self):
        path = get_sound_path("complete", "linux")
        assert path == "/usr/share/sounds/freedesktop/stereo/complete.oga"

    def test_linux_attention(self):
        path = get_sound_path("attention", "linux")
        assert path == "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"

    def test_macos_complete(self):
        path = get_sound_path("complete", "macos")
        assert path == "/System/Library/Sounds/Glass.aiff"

    def test_macos_attention(self):
        path = get_sound_path("attention", "macos")
        assert path == "/System/Library/Sounds/Basso.aiff"

    def test_windows_complete(self):
        path = get_sound_path("complete", "windows")
        assert path == r"C:\Windows\Media\Windows Notify System Generic.wav"

    def test_windows_attention(self):
        path = get_sound_path("attention", "windows")
        assert path == r"C:\Windows\Media\Windows Notify Email.wav"

    def test_env_override_complete(self):
        with patch.dict(os.environ, {"CLAUDE_NOTIFY_SOUND_FILE": "/custom/sound.wav"}):
            path = get_sound_path("complete", "linux")
            assert path == "/custom/sound.wav"

    def test_env_override_attention(self):
        with patch.dict(os.environ, {"CLAUDE_ACTION_SOUND_FILE": "/custom/alert.wav"}):
            path = get_sound_path("attention", "macos")
            assert path == "/custom/alert.wav"


class TestSendNotification:
    @patch("subprocess.Popen")
    def test_linux_notification(self, mock_popen):
        with patch("platform_utils.detect_os", return_value="linux"):
            send_notification("Test Title", "Test Body", "normal")
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "notify-send"
            assert "--app-name" in cmd
            assert "Claude Code" in cmd
            assert "--urgency" in cmd
            assert "normal" in cmd
            assert "Test Title" in cmd
            assert "Test Body" in cmd

    @patch("subprocess.Popen")
    def test_linux_critical_urgency(self, mock_popen):
        with patch("platform_utils.detect_os", return_value="linux"):
            send_notification("Alert", "Urgent", "critical")
            cmd = mock_popen.call_args[0][0]
            assert "critical" in cmd

    @patch("subprocess.Popen")
    def test_macos_notification(self, mock_popen):
        with patch("platform_utils.detect_os", return_value="macos"):
            send_notification("Test Title", "Test Body", "normal")
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "osascript"
            assert "-e" in cmd

    @patch("subprocess.Popen")
    def test_windows_notification(self, mock_popen):
        with patch("platform_utils.detect_os", return_value="windows"):
            send_notification("Test Title", "Test Body", "normal")
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "powershell"


class TestPlaySound:
    @patch("os.path.exists", return_value=True)
    @patch("subprocess.Popen")
    def test_linux_uses_paplay(self, mock_popen, mock_exists):
        with patch("platform_utils.detect_os", return_value="linux"):
            play_sound("complete")
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "paplay"

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.Popen")
    def test_linux_fallback_to_aplay(self, mock_popen, mock_exists):
        mock_popen.side_effect = [FileNotFoundError(), MagicMock()]
        with patch("platform_utils.detect_os", return_value="linux"):
            play_sound("complete")
            assert mock_popen.call_count == 2
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "aplay"

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.Popen")
    def test_macos_uses_afplay(self, mock_popen, mock_exists):
        with patch("platform_utils.detect_os", return_value="macos"):
            play_sound("attention")
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "afplay"

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.Popen")
    def test_windows_uses_powershell(self, mock_popen, mock_exists):
        with patch("platform_utils.detect_os", return_value="windows"):
            play_sound("complete")
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "powershell"

    @patch("os.path.exists", return_value=False)
    @patch("subprocess.Popen")
    def test_no_sound_if_file_missing(self, mock_popen, mock_exists):
        with patch("platform_utils.detect_os", return_value="linux"):
            result = play_sound("complete")
            assert result is False
            mock_popen.assert_not_called()
