#!/usr/bin/env python3
"""
Claude Code Notification Hook - User Action Required
Sends desktop notification when Claude needs user input.
"""

import json
import subprocess
import sys
import os
from typing import Optional

# Configuration environment variables
ENABLE_SOUND = os.environ.get("CLAUDE_ACTION_SOUND", "1") == "1"
SOUND_FILE = os.environ.get(
    "CLAUDE_ACTION_SOUND_FILE",
    "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"
)
NOTIFICATION_TIMEOUT_MS = 10000
APP_NAME = "Claude Code"
ICON = "dialog-question"


def read_stdin() -> Optional[dict]:
    """Read and parse JSON from stdin.

    Returns:
        Parsed JSON dict or None if input is empty or invalid
    """
    try:
        data = sys.stdin.read()
        if not data.strip():
            return None
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def get_notification_urgency(notification_type: str) -> str:
    """Map notification type to urgency level.

    Args:
        notification_type: Type of notification

    Returns:
        Urgency level: "critical", "normal", or "low"
    """
    urgency_map = {
        "permission_prompt": "critical",
        "idle_prompt": "normal",
    }
    return urgency_map.get(notification_type, "normal")


def get_notification_title(notification_type: str) -> str:
    """Map notification type to title.

    Args:
        notification_type: Type of notification

    Returns:
        Notification title string
    """
    title_map = {
        "permission_prompt": "Claude Code - Permission Required",
        "idle_prompt": "Claude Code - Awaiting Your Input",
    }
    return title_map.get(notification_type, "Claude Code - Action Required")


def send_notification(title: str, body: str, urgency: str = "normal") -> bool:
    """Send desktop notification using notify-send.

    Args:
        title: Notification title
        body: Notification body text
        urgency: Urgency level (critical, normal, low)

    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        cmd = [
            "notify-send",
            "--app-name", APP_NAME,
            "--icon", ICON,
            "--expire-time", str(NOTIFICATION_TIMEOUT_MS),
            "--urgency", urgency,
            title,
            body
        ]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def play_sound() -> bool:
    """Play notification sound using paplay or aplay.

    Returns:
        True if sound played successfully, False otherwise
    """
    if not ENABLE_SOUND:
        return True
    if not os.path.exists(SOUND_FILE):
        return False
    try:
        subprocess.Popen(["paplay", SOUND_FILE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        try:
            subprocess.Popen(["aplay", "-q", SOUND_FILE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False


def main() -> int:
    """Main entry point for the notification hook.

    Reads JSON from stdin, determines notification type, and sends
    appropriate desktop notification with sound.

    Returns:
        Exit code (0 for success)
    """
    data = read_stdin()

    if not data:
        # Fallback for empty input
        send_notification(
            "Claude Code - Action Required",
            "Claude needs your input",
            "normal"
        )
        play_sound()
        return 0

    notification_type = data.get("notification_type", "unknown")
    message = data.get("message", "Claude needs your input")

    title = get_notification_title(notification_type)
    urgency = get_notification_urgency(notification_type)

    send_notification(title, message, urgency)
    play_sound()
    return 0


if __name__ == "__main__":
    sys.exit(main())
