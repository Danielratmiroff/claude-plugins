#!/bin/bash
# Run all hook and observability tests

cd "$(dirname "$0")/../.."  # Go to project root

echo "=== Running Hook Tests ==="
uv run pytest .claude/hooks/test_*.py -v

echo ""
echo "=== Running Observability Tests ==="
uv run pytest observability/test_observability.py -v
