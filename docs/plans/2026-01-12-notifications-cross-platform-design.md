# Cross-Platform Notifications Plugin Design

## Overview

Redesign the notifications plugin to support Linux, macOS, and Windows using only OS-native tools (no pip dependencies).

## Constraints

- No pip dependencies allowed
- No bundled sound files - use OS built-in system sounds
- Plugin can be disabled entirely if user doesn't want notifications

## Architecture

### Plugin Structure

```
plugins/notifications/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── platform.py              # Shared OS detection & utilities
│   ├── notify_finished.py       # Stop hook handler
│   └── notify_action_required.py  # Notification hook handler
└── README.md

tests/notifications/
├── __init__.py
├── test_platform.py             # Tests for OS detection, sound paths
├── test_notify_finished.py      # Tests for Stop hook logic
└── test_notify_action_required.py  # Tests for Notification hook logic
```

### Platform Detection Flow

```
platform.py
├── detect_os() → "linux" | "macos" | "windows"
├── send_notification(title, body, urgency)
│   ├── Linux:   notify-send
│   ├── macOS:   osascript (AppleScript)
│   └── Windows: PowerShell toast
├── play_sound(sound_type)
│   ├── Linux:   paplay/aplay
│   ├── macOS:   afplay
│   └── Windows: PowerShell [System.Media.SoundPlayer]
└── get_sound_path(sound_type, os)
    └── Returns appropriate system sound path
```

## platform.py Module

### Sound Paths per OS

```python
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
```

### Notification Implementation

| OS      | Method                                                              |
|---------|---------------------------------------------------------------------|
| Linux   | `notify-send --app-name "Claude Code" --urgency <level> <title> <body>` |
| macOS   | `osascript -e 'display notification "<body>" with title "<title>"'` |
| Windows | PowerShell toast via `[Windows.UI.Notifications]`                   |

### Sound Playback

| OS      | Method                                                    |
|---------|-----------------------------------------------------------|
| Linux   | `paplay <path>` (fallback: `aplay -q <path>`)             |
| macOS   | `afplay <path>`                                           |
| Windows | PowerShell `(New-Object Media.SoundPlayer '<path>').PlaySync()` |

### Environment Variable Overrides

Optional, for custom sounds:
- `CLAUDE_NOTIFY_SOUND_FILE` - custom "complete" sound path
- `CLAUDE_ACTION_SOUND_FILE` - custom "attention" sound path

## Hook Scripts

### notify_finished.py (Stop hook)

```python
#!/usr/bin/env python3
"""Stop hook - notifies when Claude finishes responding."""

import json
import sys
from platform import detect_os, send_notification, play_sound

def format_duration(ms: int) -> str:
    # ms → "Xs" or "Xm Ys"

def format_cost(cost_usd: float) -> str:
    # $0.0012 or $1.23

def build_body(data: dict) -> str:
    # Extract from stop_hook_data:
    # - Status (end_turn → "Completed", etc.)
    # - Duration
    # - Turns
    # - Cost
    # - Tokens (in/out)

def main() -> int:
    data = json.loads(sys.stdin.read()) if sys.stdin else {}
    send_notification("Claude Code - Finished", build_body(data))
    play_sound("complete")
    return 0
```

### notify_action_required.py (Notification hook)

```python
#!/usr/bin/env python3
"""Notification hook - alerts when Claude needs user input."""

import json
import sys
from platform import detect_os, send_notification, play_sound

URGENCY_MAP = {
    "permission_prompt": "critical",
    "idle_prompt": "normal",
}

TITLE_MAP = {
    "permission_prompt": "Claude Code - Permission Required",
    "idle_prompt": "Claude Code - Awaiting Input",
}

def main() -> int:
    data = json.loads(sys.stdin.read()) if sys.stdin else {}
    notification_type = data.get("notification_type", "unknown")
    message = data.get("message", "Claude needs your input")

    title = TITLE_MAP.get(notification_type, "Claude Code - Action Required")
    urgency = URGENCY_MAP.get(notification_type, "normal")

    send_notification(title, message, urgency)
    play_sound("attention")
    return 0
```

## Tests

### test_platform.py

```python
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

class TestGetSoundPath:
    def test_linux_complete(self):
        assert get_sound_path("complete", "linux") == "/usr/share/sounds/..."

    def test_env_override(self):
        with patch.dict(os.environ, {"CLAUDE_NOTIFY_SOUND_FILE": "/custom.wav"}):
            assert get_sound_path("complete", "linux") == "/custom.wav"

class TestSendNotification:
    @patch("subprocess.Popen")
    def test_linux_builds_correct_command(self, mock_popen):
        with patch("platform.system", return_value="Linux"):
            send_notification("Title", "Body", "normal")
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "notify-send"
            assert "--urgency" in cmd

class TestPlaySound:
    @patch("subprocess.Popen")
    def test_macos_uses_afplay(self, mock_popen):
        with patch("platform.system", return_value="Darwin"):
            play_sound("complete")
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "afplay"
```

### test_notify_finished.py / test_notify_action_required.py

- Test `build_body()` with various stop_hook_data payloads
- Test JSON parsing with empty/malformed input
- Test title/urgency mapping

## Configuration Files

### hooks/hooks.json

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notify_finished.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notify_action_required.py"
          }
        ]
      }
    ]
  }
}
```

### plugin.json

```json
{
  "name": "notifications",
  "version": "0.2.0",
  "description": "Cross-platform desktop notifications for Claude Code"
}
```

## README.md Key Sections

- **What it does**: Desktop notifications + sounds when Claude finishes or needs input
- **Platform support**: Linux, macOS, Windows
- **Requirements per OS**:
  - Linux: `notify-send` (libnotify), `paplay` or `aplay`
  - macOS: None (uses built-in `osascript`, `afplay`)
  - Windows: PowerShell 5.0+
- **Configuration**: Optional env vars for custom sound paths
- **Context cost**: Zero tokens (exits with code 0)
