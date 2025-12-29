# test-runner

Automatically runs tests in background when source or test files are modified.

## What it does

This plugin triggers after `Edit` or `Write` tool calls and runs your test suite in a background process. Tests run non-blocking so Claude continues working.

## Features

- **Background execution**: Tests run in a forked process
- **Debouncing**: Prevents rapid re-triggers (default 5 seconds)
- **Locking**: Prevents concurrent test runs
- **Timeout**: Configurable timeout (default 60 seconds)

## Installation

```bash
/plugin install danielr/test-runner
```

## Configuration

Set these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_TEST_COMMAND` | (none) | Test command to run (required) |
| `CLAUDE_TEST_TIMEOUT` | `60` | Timeout in seconds |
| `CLAUDE_TEST_DEBOUNCE` | `5` | Debounce interval in seconds |
| `CLAUDE_TEST_ENABLED` | `1` | Set to `0` to disable |

Example:
```bash
export CLAUDE_TEST_COMMAND="npm test"
```

## Context cost

Zero tokens. Tests run in background, exits with code 0.

## Logs

Test output is logged to `.claude/logs/test-runner/test_runs.log` in the project directory.
