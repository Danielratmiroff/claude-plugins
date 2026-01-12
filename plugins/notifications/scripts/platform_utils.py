#!/usr/bin/env python3
"""Cross-platform utilities for notifications."""

import os
import platform as _platform
from typing import Literal

OSType = Literal["linux", "macos", "windows"]
SoundType = Literal["complete", "attention"]

SOUND_PATHS = {
    "linux": {
        "complete": "/usr/share/sounds/freedesktop/stereo/complete.oga",
        "attention": "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga",
    },
    "macos": {
        "complete": "/System/Library/Sounds/Glass.aiff",
        "attention": "/System/Library/Sounds/Basso.aiff",
    },
    "windows": {
        "complete": r"C:\Windows\Media\Windows Notify System Generic.wav",
        "attention": r"C:\Windows\Media\Windows Notify Email.wav",
    },
}

ENV_SOUND_VARS = {
    "complete": "CLAUDE_NOTIFY_SOUND_FILE",
    "attention": "CLAUDE_ACTION_SOUND_FILE",
}


def detect_os() -> OSType:
    """Detect the current operating system."""
    system = _platform.system()
    if system == "Darwin":
        return "macos"
    elif system == "Windows":
        return "windows"
    else:
        return "linux"


def get_sound_path(sound_type: SoundType, os_type: OSType) -> str:
    """Get the sound file path for the given type and OS."""
    env_var = ENV_SOUND_VARS.get(sound_type)
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]
    return SOUND_PATHS[os_type][sound_type]
