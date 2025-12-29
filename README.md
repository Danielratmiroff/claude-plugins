# Claude Plugins

A collection of Claude Code plugins for enhanced safety, observability, testing, and notifications.

## Plugins

| Plugin | Description | Context Cost |
|--------|-------------|--------------|
| [bash-safety](plugins/bash-safety/) | Block dangerous bash commands | ~50-200 bytes ONLY on block |
| [observability](plugins/observability/) | Stream tool events to JSONL | 0 tokens |
| [test-runner](plugins/test-runner/) | Auto-run tests on file changes | 0 tokens |
| [notifications](plugins/notifications/) | Desktop notifications | 0 tokens |

## Installation

### From Claude Marketplace

```bash
/plugin install danielr/bash-safety
/plugin install danielr/observability
/plugin install danielr/test-runner
/plugin install danielr/notifications
```

### Local Development

Test plugins locally during development:

```bash
claude --plugin-dir ./plugins/bash-safety
claude --plugin-dir ./plugins/observability
```

## Configuration

### test-runner

```bash
export CLAUDE_TEST_COMMAND="npm test"
export CLAUDE_TEST_TIMEOUT="60"
export CLAUDE_TEST_DEBOUNCE="5"
```

### notifications

```bash
export CLAUDE_NOTIFY_SOUND="1"
export CLAUDE_NOTIFY_SOUND_FILE="/usr/share/sounds/freedesktop/stereo/complete.oga"
export CLAUDE_ACTION_SOUND="1"
export CLAUDE_ACTION_SOUND_FILE="/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"
```

## Log Locations

All plugins log to `.claude/logs/` in the project directory:

```
.claude/logs/
├── blocked_commands.log      # bash-safety
├── events/
│   └── tool_events.jsonl     # observability
└── test-runner/
    └── test_runs.log         # test-runner
```

## Observability Dashboard

The observability dashboard reads events from the log files:

```bash
python observability/dashboard.py
```

## Context Optimization

All plugins are designed for minimal context impact:

- Exit code 0 = zero context (logging hooks)
- Exit code 2 = stderr added to context (blocking hooks like bash-safety)
- Background execution for long-running tasks (test-runner)
- Debouncing to prevent redundant executions

## License

MIT
