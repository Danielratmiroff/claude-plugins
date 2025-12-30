# Claude Plugins

[![Tests](https://github.com/Danielratmiroff/.claude/actions/workflows/tests.yml/badge.svg)](https://github.com/Danielratmiroff/.claude/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/Danielratmiroff/claude-plugins/graph/badge.svg)](https://codecov.io/gh/Danielratmiroff/claude-plugins)

A collection of Claude Code plugins for enhanced safety, observability, testing, and notifications.

## Plugins

| Plugin | Description | Context Cost |
|--------|-------------|--------------|
| [bash-safety](plugins/bash-safety/) | Block dangerous bash commands | ~50-200 bytes ONLY on block |
| [observability](plugins/observability/) | Stream tool events to JSONL | 0 tokens |
| [test-runner](plugins/test-runner/) | Auto-run tests on file changes | 0 tokens |
| [notifications](plugins/notifications/) | Desktop notifications | 0 tokens |

## Installation

First, add this marketplace to your Claude Code installation:

```bash
/plugin marketplace add https://github.com/Danielratmiroff/claude-plugins
```

### Install Individual Plugins
After adding the marketplace, install any plugin:

```bash
/plugin install {plugin-name}@Danielratmiroff
```

Example:
```bash
/plugin install bash-safety@Danielratmiroff
/plugin install observability@Danielratmiroff
/plugin install test-runner@Danielratmiroff
/plugin install notifications@Danielratmiroff
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
├── observability.jsonl       # observability
└── test-runner.jsonl         # test-runner
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
