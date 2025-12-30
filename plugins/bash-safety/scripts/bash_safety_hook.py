#!/usr/bin/env python3
"""
Claude Code Hook: Bash Safety Validator
Exit Codes: 0=allow, 1=internal error, 2=block command
"""

import json
import re
import sys
import os
from pathlib import Path
from typing import Optional

from shared.logging import get_logger

# Portable log directory - falls back to .claude/logs/ in project directory
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
LOG_DIR = PROJECT_DIR / ".claude" / "logs"
LOG_FILE = LOG_DIR / "bash-safety.jsonl"
ENABLE_LOGGING = True

_logger = None
def get_plugin_logger():
    global _logger
    if _logger is None and ENABLE_LOGGING:
        _logger = get_logger("bash-safety", LOG_FILE)
    return _logger

# Dangerous patterns
DESTRUCTIVE_PATTERNS = [
    # rm -r / variants - handle multiline and various flag combinations
    (r"rm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)*(/\s*$|/\s*[;&|]|/\s*\n)", "CRITICAL: Recursive deletion of root filesystem"),
    (r"rm\s+.*-[a-zA-Z]*r[a-zA-Z]*.*\s+/\*", "CRITICAL: Recursive deletion of all root contents"),
    # System directory deletion - more flexible pattern for flag ordering
    (r"rm\s+(-[a-zA-Z]+\s+)*-[a-zA-Z]*r[a-zA-Z]*(\s+-[a-zA-Z]+)*\s+(/|/bin|/boot|/dev|/etc|/home|/lib|/opt|/root|/sbin|/sys|/usr|/var)(\s|$|[;&|])",
     "CRITICAL: Attempted recursive deletion of system directory"),
    # --no-preserve-root is always dangerous
    (r"rm\s+.*--no-preserve-root", "CRITICAL: Attempt to bypass root filesystem protection"),
    # Filesystem operations
    (r"mkfs\.", "CRITICAL: Filesystem format operation"),
    (r"dd\s+.*of=/dev/(sd[a-z]|nvme|hd[a-z]|vd[a-z])", "CRITICAL: Direct disk write"),
    # Disk destruction tools
    (r"\bshred\s+.*(/dev/(sd[a-z]|nvme|hd[a-z]|vd[a-z])|/dev/[a-z]+[0-9]*)", "CRITICAL: Disk shredding operation"),
    (r"\bwipefs\s+", "CRITICAL: Filesystem signature wiping"),
]

RESOURCE_EXHAUSTION_PATTERNS = [
    # Classic fork bomb and variants with any single-char function name
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;?\s*:", "CRITICAL: Fork bomb detected"),
    # Generic fork bomb pattern: func(){ func|func& };func
    (r"\b(\w)\(\)\s*\{\s*\1\s*\|\s*\1\s*&\s*\}\s*;?\s*\1\b", "CRITICAL: Fork bomb detected (generic pattern)"),
    (r"while\s*(true|1|:)\s*;\s*do\s*(cat|yes|dd)", "WARNING: Infinite resource consumption loop"),
]

NETWORK_PATTERNS = [
    (r"(nc|ncat|netcat)\s+.*-e\s*/bin/(ba)?sh", "CRITICAL: Reverse shell attempt"),
    (r"bash\s+-i\s+>&\s*/dev/tcp/", "CRITICAL: Bash reverse shell"),
    # Remote script execution - bash, sh, and python variants
    (r"(curl|wget)\s+.*\|\s*(ba)?sh", "WARNING: Remote script execution via pipe to shell"),
    (r"(curl|wget)\s+.*\|\s*python[23]?", "WARNING: Remote script execution via pipe to python"),
    (r"(curl|wget)\s+.*\|\s*sudo", "CRITICAL: Remote script with sudo"),
]

PRIVILEGE_PATTERNS = [
    # Auth file modifications - both overwrite (>) and append (>>)
    (r">\s*/etc/(passwd|shadow|sudoers)", "CRITICAL: Attempt to overwrite auth files"),
    (r">>\s*/etc/(passwd|shadow|sudoers)", "CRITICAL: Attempt to append to auth files"),
    # tee to auth files (common privilege escalation technique)
    (r"\btee\s+(-[a-zA-Z]+\s+)*(/etc/(passwd|shadow|sudoers)|/etc/sudoers\.d/)", "CRITICAL: Attempt to write to auth files via tee"),
    (r"chmod\s+(-[a-zA-Z]+\s+)*777\s+/", "CRITICAL: Dangerous permission change"),
]

ALL_PATTERNS = DESTRUCTIVE_PATTERNS + RESOURCE_EXHAUSTION_PATTERNS + NETWORK_PATTERNS + PRIVILEGE_PATTERNS

def validate_command(command: str) -> list[tuple[str, str]]:
    issues = []
    for pattern, message in ALL_PATTERNS:
        try:
            # Use MULTILINE to make $ match end of line (for multiline commands)
            if re.search(pattern, command.strip(), re.IGNORECASE | re.MULTILINE):
                issues.append((pattern, message))
        except re.error:
            pass
    return issues

def log_blocked_command(command: str, issues: list[tuple[str, str]]) -> None:
    logger = get_plugin_logger()
    if logger is None:
        return
    reasons = [msg for _, msg in issues]
    logger.warning(
        "Blocked dangerous command",
        extra={
            "event": "command_blocked",
            "command": command,
            "reasons": reasons,
        }
    )

def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(1)

    if input_data.get("tool_name") != "Bash":
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    issues = validate_command(command)
    if issues:
        log_blocked_command(command, issues)
        print("BLOCKED: Dangerous command detected!", file=sys.stderr)
        for _, msg in issues:
            print(f"  - {msg}", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
