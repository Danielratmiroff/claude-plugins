#!/bin/bash
set -euo pipefail

# Run all tests with coverage using UV.
# Pass --coverage to also write the XML report.
generate_xml=0

if [[ ${1-} == "--coverage" ]]; then
  generate_xml=1
  shift
fi

cmd=(
  uv run --group dev pytest
  --cov=plugins --cov=shared --cov=observability
  --cov-report=term-missing
)

if [[ $generate_xml -eq 1 ]]; then
  cmd+=(--cov-report=xml)
fi

"${cmd[@]}"
