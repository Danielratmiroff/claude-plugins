# notifications

Cross-platform desktop notifications for Claude Code events.

## What it does

This plugin sends desktop notifications:
- **Stop hook**: When Claude finishes responding (shows duration, cost, token counts)
- **Notification hook**: When Claude needs user input (permission prompts, idle prompts)

## Features

- Cross-platform support (Linux, macOS, Windows)
- Desktop notifications using native OS tools
- Audio alerts using native OS tools
- Configurable sound files via environment variables
- Different urgency levels for different notification types

## Installation

```bash
/plugin install danielr/notifications
```

## Platform Support

| Platform | Notifications | Sound |
|----------|---------------|-------|
| Linux | `notify-send` | `paplay` / `aplay` |
| macOS | `osascript` | `afplay` |
| Windows | PowerShell Toast | PowerShell SoundPlayer |

## Configuration

Custom sound files can be configured via environment variables:

| Variable | Description |
|----------|-------------|
| `CLAUDE_NOTIFY_SOUND_FILE` | Custom completion sound file path |
| `CLAUDE_ACTION_SOUND_FILE` | Custom action-required sound file path |

### Default Sound Paths

**Linux:**
- Complete: `/usr/share/sounds/freedesktop/stereo/complete.oga`
- Attention: `/usr/share/sounds/freedesktop/stereo/message-new-instant.oga`

**macOS:**
- Complete: `/System/Library/Sounds/Glass.aiff`
- Attention: `/System/Library/Sounds/Basso.aiff`

**Windows:**
- Complete: `C:\Windows\Media\Windows Notify System Generic.wav`
- Attention: `C:\Windows\Media\Windows Notify Email.wav`

## Context cost

Zero tokens. Desktop notification only, exits with code 0.

## Requirements

- **Linux**: `notify-send` (libnotify), optionally `paplay` (PulseAudio) or `aplay` (ALSA)
- **macOS**: Built-in `osascript` and `afplay`
- **Windows**: PowerShell (included by default)
