#!/bin/bash
# test-plugins.sh
claude \
--plugin-dir "$(pwd)/plugins/bash-safety" \
--plugin-dir "$(pwd)/plugins/observability" \
--plugin-dir "$(pwd)/plugins/test-runner" \
--plugin-dir "$(pwd)/plugins/notifications" \
"$@"
