# Cross-Platform Notifications Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the notifications plugin work on Linux, macOS, and Windows using only OS-native tools.

**Architecture:** Single `platform.py` module handles OS detection, notifications, and sounds. Two hook scripts (`notify_finished.py`, `notify_action_required.py`) import from platform module. All subprocess calls use OS-native commands.

**Tech Stack:** Python 3 standard library only (subprocess, platform, json, os, sys). No pip dependencies.

---

## Task 1: Create platform.py with OS detection

**Files:**
- Create: `plugins/notifications/scripts/platform.py`
- Create: `tests/notifications/__init__.py`
- Create: `tests/notifications/test_platform.py`

**Step 1: Create test directory and init file**

```bash
mkdir -p tests/notifications
touch tests/notifications/__init__.py
```

**Step 2: Write failing test for detect_os()**

Create `tests/notifications/test_platform.py`:

```python
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
```

**Step 3: Run test to verify it fails**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_platform.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 4: Write minimal implementation**

Create `plugins/notifications/scripts/platform_utils.py`:

```python
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
```

**Step 5: Run test to verify it passes**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_platform.py::TestDetectOS -v`
Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add plugins/notifications/scripts/platform_utils.py tests/notifications/
git commit -m "feat(notifications): add OS detection for cross-platform support"
```

---

## Task 2: Add sound path resolution

**Files:**
- Modify: `plugins/notifications/scripts/platform_utils.py`
- Modify: `tests/notifications/test_platform.py`

**Step 1: Write failing test for get_sound_path()**

Add to `tests/notifications/test_platform.py`:

```python
from platform_utils import detect_os, get_sound_path


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
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_platform.py::TestGetSoundPath -v`
Expected: FAIL with ImportError (get_sound_path not defined)

**Step 3: Write implementation**

Add to `plugins/notifications/scripts/platform_utils.py`:

```python
import os

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


def get_sound_path(sound_type: SoundType, os_type: OSType) -> str:
    """Get the sound file path for the given type and OS."""
    env_var = ENV_SOUND_VARS.get(sound_type)
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]
    return SOUND_PATHS[os_type][sound_type]
```

**Step 4: Run test to verify it passes**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_platform.py::TestGetSoundPath -v`
Expected: PASS (8 tests)

**Step 5: Commit**

```bash
git add plugins/notifications/scripts/platform_utils.py tests/notifications/test_platform.py
git commit -m "feat(notifications): add sound path resolution with env overrides"
```

---

## Task 3: Add send_notification function

**Files:**
- Modify: `plugins/notifications/scripts/platform_utils.py`
- Modify: `tests/notifications/test_platform.py`

**Step 1: Write failing tests for send_notification()**

Add to `tests/notifications/test_platform.py`:

```python
from unittest.mock import patch, MagicMock
from platform_utils import detect_os, get_sound_path, send_notification


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
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_platform.py::TestSendNotification -v`
Expected: FAIL with ImportError

**Step 3: Write implementation**

Add to `plugins/notifications/scripts/platform_utils.py`:

```python
import subprocess

APP_NAME = "Claude Code"


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
```

**Step 4: Run test to verify it passes**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_platform.py::TestSendNotification -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add plugins/notifications/scripts/platform_utils.py tests/notifications/test_platform.py
git commit -m "feat(notifications): add cross-platform send_notification function"
```

---

## Task 4: Add play_sound function

**Files:**
- Modify: `plugins/notifications/scripts/platform_utils.py`
- Modify: `tests/notifications/test_platform.py`

**Step 1: Write failing tests for play_sound()**

Add to `tests/notifications/test_platform.py`:

```python
from platform_utils import detect_os, get_sound_path, send_notification, play_sound


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
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_platform.py::TestPlaySound -v`
Expected: FAIL with ImportError

**Step 3: Write implementation**

Add to `plugins/notifications/scripts/platform_utils.py`:

```python
def play_sound(sound_type: SoundType) -> bool:
    """Play a notification sound. Returns True on success."""
    os_type = detect_os()
    sound_path = get_sound_path(sound_type, os_type)

    if not os.path.exists(sound_path):
        return False

    try:
        if os_type == "linux":
            try:
                subprocess.Popen(["paplay", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                subprocess.Popen(["aplay", "-q", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif os_type == "macos":
            subprocess.Popen(["afplay", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:  # windows
            script = f"(New-Object Media.SoundPlayer '{sound_path}').PlaySync()"
            subprocess.Popen(["powershell", "-Command", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False
```

**Step 4: Run test to verify it passes**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_platform.py::TestPlaySound -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add plugins/notifications/scripts/platform_utils.py tests/notifications/test_platform.py
git commit -m "feat(notifications): add cross-platform play_sound function"
```

---

## Task 5: Update notify_finished.py to use platform_utils

**Files:**
- Modify: `plugins/notifications/scripts/notify_finished.py`
- Create: `tests/notifications/test_notify_finished.py`

**Step 1: Write tests for notify_finished.py**

Create `tests/notifications/test_notify_finished.py`:

```python
import pytest
import json
import sys
import os
from unittest.mock import patch, MagicMock
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/notifications/scripts'))

from notify_finished import format_duration, format_cost, build_notification_body, main


class TestFormatDuration:
    def test_milliseconds(self):
        assert format_duration(500) == "500ms"

    def test_seconds(self):
        assert format_duration(5000) == "5.0s"

    def test_minutes(self):
        assert format_duration(125000) == "2m 5s"


class TestFormatCost:
    def test_small_cost(self):
        assert format_cost(0.0012) == "$0.0012"

    def test_normal_cost(self):
        assert format_cost(1.23) == "$1.23"


class TestBuildNotificationBody:
    def test_full_data(self):
        data = {
            "stop_hook_data": {
                "stop_reason": "end_turn",
                "duration_ms": 5000,
                "num_turns": 3,
                "total_cost_usd": 0.05,
                "total_input_tokens": 1000,
                "total_output_tokens": 500
            }
        }
        body = build_notification_body(data)
        assert "Completed" in body
        assert "5.0s" in body
        assert "3" in body
        assert "$0.05" in body
        assert "1,000" in body
        assert "500" in body

    def test_empty_data(self):
        body = build_notification_body({})
        assert "Completed" in body


class TestMain:
    @patch("notify_finished.play_sound")
    @patch("notify_finished.send_notification")
    def test_main_with_data(self, mock_notify, mock_sound):
        data = {"stop_hook_data": {"stop_reason": "end_turn", "duration_ms": 1000}}
        with patch("sys.stdin", StringIO(json.dumps(data))):
            result = main()
        assert result == 0
        mock_notify.assert_called_once()
        mock_sound.assert_called_once_with("complete")

    @patch("notify_finished.play_sound")
    @patch("notify_finished.send_notification")
    def test_main_with_empty_stdin(self, mock_notify, mock_sound):
        with patch("sys.stdin", StringIO("")):
            result = main()
        assert result == 0
        mock_notify.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_notify_finished.py -v`
Expected: FAIL (imports won't match new structure)

**Step 3: Rewrite notify_finished.py**

Replace `plugins/notifications/scripts/notify_finished.py`:

```python
#!/usr/bin/env python3
"""
Claude Code Stop Hook - "When Finished" Notification
Sends desktop notification and plays sound when Claude finishes responding.
"""

import json
import sys
from typing import Optional

from platform_utils import send_notification, play_sound

NOTIFICATION_TITLE = "Claude Code - Finished"


def format_duration(ms: int) -> str:
    """Format milliseconds as human-readable duration."""
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def format_cost(cost_usd: float) -> str:
    """Format cost in USD."""
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    return f"${cost_usd:.2f}"


def read_stdin() -> Optional[dict]:
    """Read and parse JSON from stdin."""
    try:
        data = sys.stdin.read()
        if not data.strip():
            return None
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def build_notification_body(data: dict) -> str:
    """Build notification body from stop hook data."""
    stop_data = data.get("stop_hook_data", {})
    parts = []

    reason_map = {
        "end_turn": "Completed",
        "tool_use": "Tool executed",
        "max_tokens": "Token limit reached",
        "stop_sequence": "Stop sequence hit"
    }

    reason = stop_data.get("stop_reason", "end_turn")
    parts.append(f"Status: {reason_map.get(reason, reason)}")

    duration_ms = stop_data.get("duration_ms")
    if duration_ms:
        parts.append(f"Duration: {format_duration(duration_ms)}")

    num_turns = stop_data.get("num_turns")
    if num_turns:
        parts.append(f"Turns: {num_turns}")

    cost = stop_data.get("total_cost_usd")
    if cost and cost > 0:
        parts.append(f"Cost: {format_cost(cost)}")

    input_tokens = stop_data.get("total_input_tokens", 0)
    output_tokens = stop_data.get("total_output_tokens", 0)
    if input_tokens or output_tokens:
        parts.append(f"Tokens: {input_tokens:,} in / {output_tokens:,} out")

    return "\n".join(parts)


def main() -> int:
    """Main entry point for the stop hook."""
    data = read_stdin() or {}
    body = build_notification_body(data)
    send_notification(NOTIFICATION_TITLE, body)
    play_sound("complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: Run test to verify it passes**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_notify_finished.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add plugins/notifications/scripts/notify_finished.py tests/notifications/test_notify_finished.py
git commit -m "refactor(notifications): update notify_finished to use platform_utils"
```

---

## Task 6: Update notify_action_required.py to use platform_utils

**Files:**
- Modify: `plugins/notifications/scripts/notify_action_required.py`
- Create: `tests/notifications/test_notify_action_required.py`

**Step 1: Write tests for notify_action_required.py**

Create `tests/notifications/test_notify_action_required.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_notify_action_required.py -v`
Expected: FAIL

**Step 3: Rewrite notify_action_required.py**

Replace `plugins/notifications/scripts/notify_action_required.py`:

```python
#!/usr/bin/env python3
"""
Claude Code Notification Hook - User Action Required
Sends desktop notification when Claude needs user input.
"""

import json
import sys
from typing import Optional

from platform_utils import send_notification, play_sound

URGENCY_MAP = {
    "permission_prompt": "critical",
    "idle_prompt": "normal",
}

TITLE_MAP = {
    "permission_prompt": "Claude Code - Permission Required",
    "idle_prompt": "Claude Code - Awaiting Input",
}

DEFAULT_TITLE = "Claude Code - Action Required"
DEFAULT_MESSAGE = "Claude needs your input"


def get_notification_title(notification_type: str) -> str:
    """Map notification type to title."""
    return TITLE_MAP.get(notification_type, DEFAULT_TITLE)


def get_notification_urgency(notification_type: str) -> str:
    """Map notification type to urgency level."""
    return URGENCY_MAP.get(notification_type, "normal")


def read_stdin() -> Optional[dict]:
    """Read and parse JSON from stdin."""
    try:
        data = sys.stdin.read()
        if not data.strip():
            return None
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def main() -> int:
    """Main entry point for the notification hook."""
    data = read_stdin() or {}

    notification_type = data.get("notification_type", "unknown")
    message = data.get("message", DEFAULT_MESSAGE)

    title = get_notification_title(notification_type)
    urgency = get_notification_urgency(notification_type)

    send_notification(title, message, urgency)
    play_sound("attention")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: Run test to verify it passes**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/test_notify_action_required.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add plugins/notifications/scripts/notify_action_required.py tests/notifications/test_notify_action_required.py
git commit -m "refactor(notifications): update notify_action_required to use platform_utils"
```

---

## Task 7: Update plugin metadata and README

**Files:**
- Modify: `plugins/notifications/.claude-plugin/plugin.json`
- Modify: `plugins/notifications/README.md`

**Step 1: Update plugin.json**

Replace `plugins/notifications/.claude-plugin/plugin.json`:

```json
{
  "name": "notifications",
  "version": "0.2.0",
  "description": "Cross-platform desktop notifications for Claude Code",
  "author": {
    "name": "danielr"
  }
}
```

**Step 2: Update README.md**

Replace `plugins/notifications/README.md`:

```markdown
# notifications

Cross-platform desktop notifications for Claude Code events.

## What it does

This plugin sends desktop notifications:
- **Stop hook**: When Claude finishes responding (shows duration, cost, token counts)
- **Notification hook**: When Claude needs user input (permission prompts, idle prompts)

## Platform Support

| OS | Notifications | Sounds |
|----|---------------|--------|
| Linux | `notify-send` | `paplay` / `aplay` |
| macOS | `osascript` | `afplay` |
| Windows | PowerShell toast | PowerShell SoundPlayer |

## Installation

```bash
/plugin install danielr/notifications
```

## Requirements

**Linux:**
- `notify-send` (libnotify) - usually pre-installed
- `paplay` (PulseAudio) or `aplay` (ALSA) for sounds

**macOS:**
- No additional requirements (uses built-in tools)

**Windows:**
- PowerShell 5.0+ (included in Windows 10+)

## Configuration

Optional environment variables to use custom sound files:

| Variable | Description |
|----------|-------------|
| `CLAUDE_NOTIFY_SOUND_FILE` | Custom sound for task completion |
| `CLAUDE_ACTION_SOUND_FILE` | Custom sound for action required |

## Default Sounds

| OS | Completion | Action Required |
|----|------------|-----------------|
| Linux | `complete.oga` | `message-new-instant.oga` |
| macOS | `Glass.aiff` | `Basso.aiff` |
| Windows | `Windows Notify System Generic.wav` | `Windows Notify Email.wav` |

## Context cost

Zero tokens. Desktop notification only, exits with code 0.
```

**Step 3: Commit**

```bash
git add plugins/notifications/.claude-plugin/plugin.json plugins/notifications/README.md
git commit -m "docs(notifications): update for cross-platform support"
```

---

## Task 8: Run full test suite and verify

**Step 1: Run all notification tests**

Run: `cd /home/ubuntu/code/claude-plugins && python -m pytest tests/notifications/ -v`
Expected: All tests PASS

**Step 2: Delete old platform.py if it exists (we used platform_utils.py)**

Check if `plugins/notifications/scripts/platform.py` exists and remove if needed.

**Step 3: Final commit if any cleanup needed**

```bash
git status
# If clean, done. If changes, commit them.
```
