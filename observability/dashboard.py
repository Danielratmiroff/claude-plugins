#!/usr/bin/env python3
"""Claude Code Observability Dashboard - Real-time CLI dashboard using Rich."""
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

LOG_FILE = Path.home() / ".claude" / "logs" / "events" / "tool_events.jsonl"
REFRESH_RATE = 1.0

class EventStore:
    def __init__(self, max_events=500):
        self.events: List[Dict] = []
        self.tool_counts: Dict[str, int] = defaultdict(int)
        self.max_events = max_events
        self.success_count = 0
        self.error_count = 0

    def add_event(self, event):
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events.pop(0)
        tool_name = event.get("tool", {}).get("tool_name", "unknown")
        self.tool_counts[tool_name] += 1
        if event.get("event_type") == "PostToolUse":
            if event.get("response", {}).get("success", True):
                self.success_count += 1
            else:
                self.error_count += 1

class LogWatcher:
    def __init__(self, log_path):
        self.log_path = log_path
        self.position = 0

    def get_new_events(self):
        events = []
        if not self.log_path.exists():
            return events
        try:
            with open(self.log_path, "r") as f:
                f.seek(self.position)
                for line in f:
                    if line.strip():
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
                self.position = f.tell()
        except Exception:
            pass
        return events

def get_tool_color(tool_name):
    colors = {"Bash": "red", "Read": "blue", "Write": "green", "Edit": "yellow", "Grep": "cyan", "Glob": "magenta"}
    return colors.get(tool_name, "white")

def build_events_table(events):
    table = Table(title="Recent Events", show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Time", width=10)
    table.add_column("Instance", width=10)
    table.add_column("Type", width=10)
    table.add_column("Tool", width=12)
    table.add_column("Details", ratio=1)

    for event in reversed(events[-15:]):
        ts = event.get("timestamp", "")[:19].split("T")[-1]
        session_id = event.get("session_id", "")
        instance_display = session_id[-8:] if len(session_id) > 8 else session_id or "-"
        event_type = event.get("event_type", "").replace("ToolUse", "")
        tool = event.get("tool", {})
        tool_name = tool.get("tool_name", "unknown")
        details = tool.get("file_path") or tool.get("command", "")[:50] or tool.get("pattern") or "-"
        table.add_row(ts, instance_display, event_type, f"[{get_tool_color(tool_name)}]{tool_name}[/]", details)
    return table

def build_stats_panel(store):
    lines = [f"[bold]Total:[/bold] {sum(store.tool_counts.values())}",
             f"[green]OK:[/green] {store.success_count}  [red]Fail:[/red] {store.error_count}", ""]
    for tool, count in sorted(store.tool_counts.items(), key=lambda x: -x[1])[:6]:
        lines.append(f"  [{get_tool_color(tool)}]{tool:12}[/] {count}x")
    return Panel("\n".join(lines), title="Stats", border_style="blue")

def build_dashboard(store):
    layout = Layout()
    layout.split_column(Layout(name="header", size=3), Layout(name="main"))
    layout["main"].split_row(Layout(name="events", ratio=6), Layout(name="stats", ratio=1))
    layout["header"].update(Panel(Text("Claude Code Observability Dashboard", style="bold white on blue")))
    layout["events"].update(build_events_table(store.events))
    layout["stats"].update(build_stats_panel(store))
    return layout

def run_dashboard(log_path=None):
    console = Console()
    store = EventStore()
    watcher = LogWatcher(log_path or LOG_FILE)
    for event in watcher.get_new_events():
        store.add_event(event)
    console.print(f"[dim]Watching: {log_path or LOG_FILE}[/dim]\n[dim]Press Ctrl+C to exit[/dim]\n")
    try:
        with Live(build_dashboard(store), console=console, refresh_per_second=1) as live:
            while True:
                for event in watcher.get_new_events():
                    store.add_event(event)
                live.update(build_dashboard(store))
                time.sleep(REFRESH_RATE)
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped.[/dim]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-file", type=Path, default=LOG_FILE)
    args = parser.parse_args()
    run_dashboard(args.log_file)
