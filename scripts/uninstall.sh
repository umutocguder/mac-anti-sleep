#!/bin/bash
# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

set -euo pipefail

echo "=== Uninstalling 11Hopem AI Sleep Guard ==="

PLIST_DST="${HOME}/Library/LaunchAgents/com.11hopem.ai-sleep-guard.plist"
if [ -f "${PLIST_DST}" ]; then
    launchctl bootout "gui/$(id -u)/com.11hopem.ai-sleep-guard" 2>/dev/null || launchctl unload "${PLIST_DST}" 2>/dev/null || true
    rm -f "${PLIST_DST}"
    echo "✓ Removed LaunchAgent"
fi

rm -f "${HOME}/.local/bin/ai-sleep-guard"
echo "✓ Removed ~/.local/bin/ai-sleep-guard symlink"

# Kill any remaining caffeinate spawned by guard
pkill -f "caffeinate -d -i" 2>/dev/null || true
rm -rf /tmp/ai_sleep_guard

echo "=== Uninstallation complete. ==="
