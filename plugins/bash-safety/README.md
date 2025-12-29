# bash-safety

Pre-execution validator that blocks dangerous bash commands before they run.

## What it does

This plugin intercepts all `Bash` tool calls and validates them against a comprehensive set of dangerous patterns. If a dangerous command is detected, it blocks execution and logs the attempt.

## Blocked patterns

- **Destructive operations**: `rm -rf /`, filesystem format (`mkfs`), direct disk writes (`dd`)
- **Resource exhaustion**: Fork bombs, infinite loops
- **Network attacks**: Reverse shells, remote script execution via `curl|bash`
- **Privilege escalation**: Writing to `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`

## Installation

```bash
/plugin install danielr/bash-safety
```

## Context cost

~50-200 bytes per blocked command (stderr message). Zero cost when commands are allowed.

## Logs

Blocked commands are logged to `.claude/logs/blocked_commands.log` in the project directory.
