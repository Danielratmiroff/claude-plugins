#!/usr/bin/env python3
"""Cross-platform utilities for notifications."""

import os
import platform as _platform
import subprocess
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

APP_NAME = "Claude Code"


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


def send_notification(title: str, body: str, urgency: str = "normal") -> bool:
    """Send a desktop notification. Returns True on success."""
    os_type = detect_os()
    try:
        if os_type == "linux":
            cmd = [
                "notify-send",
                "--app-name", APP_NAME,
                "--urgency", urgency,
                title,
                body
            ]
        elif os_type == "macos":
            script = f'display notification "{body}" with title "{title}"'
            cmd = ["osascript", "-e", script]
        else:  # windows
            script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
            $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
            $xml.GetElementsByTagName("text")[0].AppendChild($xml.CreateTextNode("{title}")) | Out-Null
            $xml.GetElementsByTagName("text")[1].AppendChild($xml.CreateTextNode("{body}")) | Out-Null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Claude Code").Show($toast)
            '''
            cmd = ["powershell", "-Command", script]

        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False
