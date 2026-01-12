#!/usr/bin/env python3
"""Cross-platform utilities for notifications."""

import platform as _platform
from typing import Literal

OSType = Literal["linux", "macos", "windows"]


def detect_os() -> OSType:
    """Detect the current operating system."""
    system = _platform.system()
    if system == "Darwin":
        return "macos"
    elif system == "Windows":
        return "windows"
    else:
        return "linux"
