# observability

Non-blocking event logger that streams all tool events to JSONL format.

## What it does

This plugin captures all PreToolUse and PostToolUse events and writes them to a JSONL log file. It's designed for zero context impact - all logging happens silently.

## Logged data

Each event includes:
- `event_id`: Unique identifier
- `timestamp`: ISO 8601 UTC timestamp
- `event_type`: PreToolUse or PostToolUse
- `session_id`: Claude Code session identifier
- `tool`: Tool metadata (name, command/path/pattern/url depending on tool type)
- `hook_processing_ms`: Hook execution time

## Installation

```bash
/plugin install danielr/observability
```

## Context cost

Zero tokens. Logs to file only, exits with code 0.

## Logs

Events are logged to `.claude/logs/events/tool_events.jsonl` in the project directory. Automatic log rotation occurs at 50MB.

## Usage with dashboard

The observability dashboard can read these logs. See the main repository for dashboard usage.
