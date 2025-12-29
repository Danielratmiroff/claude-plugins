# notifications

Desktop notifications for Claude Code events.

## What it does

This plugin sends desktop notifications:
- **Stop hook**: When Claude finishes responding (shows duration, cost, token counts)
- **Notification hook**: When Claude needs user input (permission prompts, idle prompts)

## Features

- Desktop notifications via `notify-send`
- Audio alerts via `paplay` or `aplay`
- Configurable sound files
- Different urgency levels for different notification types

## Installation

```bash
/plugin install danielr/notifications
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_NOTIFY_SOUND` | `1` | Enable completion sound (`0` to disable) |
| `CLAUDE_NOTIFY_SOUND_FILE` | `/usr/share/sounds/freedesktop/stereo/complete.oga` | Completion sound file |
| `CLAUDE_ACTION_SOUND` | `1` | Enable action-required sound (`0` to disable) |
| `CLAUDE_ACTION_SOUND_FILE` | `/usr/share/sounds/freedesktop/stereo/message-new-instant.oga` | Action-required sound file |

## Context cost

Zero tokens. Desktop notification only, exits with code 0.

## Requirements

- Linux with `notify-send` (libnotify)
- Optional: `paplay` (PulseAudio) or `aplay` (ALSA) for sounds
