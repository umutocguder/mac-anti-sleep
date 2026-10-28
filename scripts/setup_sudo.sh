#!/bin/bash
# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

set -euo pipefail

CURRENT_USER="$(id -un)"
SUDOERS_FILE="/etc/sudoers.d/ai-sleep-guard"
RULE="${CURRENT_USER} ALL=(ALL) NOPASSWD: /usr/bin/pmset -a disablesleep 1, /usr/bin/pmset -a disablesleep 0, /usr/bin/pmset -g, /usr/bin/pmset sleepnow"

echo "=== Configuring Sudoers for 11Hopem AI Sleep Guard ==="
echo "Target: ${SUDOERS_FILE}"
echo "Rule:   ${RULE}"

TMP_FILE="$(mktemp /tmp/ai_sleep_guard_sudoers.XXXXXX)"
echo "${RULE}" > "${TMP_FILE}"
chmod 0440 "${TMP_FILE}"

if sudo /usr/sbin/visudo -c -f "${TMP_FILE}"; then
    sudo cp -f "${TMP_FILE}" "${SUDOERS_FILE}"
    sudo chmod 0440 "${SUDOERS_FILE}"
    rm -f "${TMP_FILE}"
    echo "✓ Sudoers file installed successfully!"
else
    echo "✗ Sudoers validation failed! Aborting for safety."
    rm -f "${TMP_FILE}"
    exit 1
fi

echo "✓ AI Sleep Guard can now manage clamshell / lid-close sleep assertions without password prompts."
