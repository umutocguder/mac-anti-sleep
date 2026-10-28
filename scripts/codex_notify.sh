#!/bin/bash
# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

# Codex Turn Notification and Sleep Guard Integration
# Signals Sleep Guard that Codex turn has ended while forwarding to SkyComputerUseClient.

set -euo pipefail

# 1. Notify sleep guard that codex turn has concluded
if command -v ai-sleep-guard >/dev/null 2>&1; then
    ai-sleep-guard done codex >/dev/null 2>&1 || true
elif [ -f "/Users/umut/.local/bin/ai-sleep-guard" ]; then
    /Users/umut/.local/bin/ai-sleep-guard done codex >/dev/null 2>&1 || true
fi

# 2. Forward to original SkyComputerUseClient notify target
ORIGINAL_CLIENT="/Users/umut/.codex/computer-use/Codex Computer Use.app/Contents/SharedSupport/SkyComputerUseClient.app/Contents/MacOS/SkyComputerUseClient"
if [ -x "${ORIGINAL_CLIENT}" ]; then
    exec "${ORIGINAL_CLIENT}" "$@"
fi
