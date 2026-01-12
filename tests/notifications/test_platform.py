import pytest
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/notifications/scripts'))

from platform_utils import detect_os


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
