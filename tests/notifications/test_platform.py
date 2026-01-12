import pytest
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/notifications/scripts'))

from platform_utils import detect_os, get_sound_path


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
