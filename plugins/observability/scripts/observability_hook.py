#!/usr/bin/env python3
"""
Claude Code Observability Hook - Streams tool events to JSONL file.
Non-blocking, fails silently.
"""
import json
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import hashlib

# Portable log directory - falls back to .claude/logs/events in project directory
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
LOG_DIR = PROJECT_DIR / ".claude" / "logs" / "events"
LOG_FILE = LOG_DIR / "tool_events.jsonl"
MAX_LOG_SIZE_MB = 50

def ensure_log_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def rotate_log_if_needed():
    if LOG_FILE.exists():
        size_mb = LOG_FILE.stat().st_size / (1024 * 1024)
        if size_mb > MAX_LOG_SIZE_MB:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            LOG_FILE.rename(LOG_FILE.with_suffix(f".{timestamp}.jsonl"))

def truncate_large_values(obj, max_length=1000):
    if isinstance(obj, str):
        return obj[:max_length] + f"... [truncated]" if len(obj) > max_length else obj
    elif isinstance(obj, dict):
        return {k: truncate_large_values(v, max_length) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [truncate_large_values(item, max_length) for item in obj]
    return obj

def extract_tool_metadata(data):
    tool_name = data.get("tool_name", "unknown")
    tool_input = data.get("tool_input", {})
    metadata = {"tool_name": tool_name}

    if tool_name == "Bash":
        metadata["command"] = tool_input.get("command", "")[:200]
    elif tool_name in ("Read", "Write", "Edit"):
        metadata["file_path"] = tool_input.get("file_path", "")
    elif tool_name in ("Grep", "Glob"):
        metadata["pattern"] = tool_input.get("pattern", "")
    elif tool_name == "WebFetch":
        metadata["url"] = tool_input.get("url", "")
    elif tool_name == "WebSearch":
        metadata["query"] = tool_input.get("query", "")

    return metadata

def build_event(data, start_time):
    event_type = data.get("hook_event_name", "unknown")
    event = {
        "event_id": hashlib.sha256(f"{data.get('session_id', '')}:{data.get('tool_use_id', '')}:{time.time_ns()}".encode()).hexdigest()[:16],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "session_id": data.get("session_id", ""),
        "tool_use_id": data.get("tool_use_id", ""),
        "cwd": data.get("cwd", ""),
        "tool": extract_tool_metadata(data),
        "hook_processing_ms": round((time.time() - start_time) * 1000, 2),
    }
    if event_type == "PostToolUse":
        response = data.get("tool_response", {})
        event["response"] = {"success": response.get("success", True) if isinstance(response, dict) else True}
    return event

def main():
    start_time = time.time()
    try:
        input_data = json.load(sys.stdin)
        event = build_event(input_data, start_time)
        ensure_log_dir()
        rotate_log_if_needed()
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")
        sys.exit(0)
    except Exception:
        sys.exit(0)  # Fail silently

if __name__ == "__main__":
    main()
