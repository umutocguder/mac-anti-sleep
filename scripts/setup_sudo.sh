#!/bin/bash
# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

set -euo pipefail

# Determine real non-root user when executed via sudo
TARGET_USER="${SUDO_USER:-${USER:-$(id -un)}}"
if [ "${TARGET_USER}" = "root" ]; then
    TARGET_USER="${LOGNAME:-umut}"
fi

SUDOERS_FILE="/etc/sudoers.d/ai-sleep-guard"
RULE="${TARGET_USER} ALL=(ALL) NOPASSWD: /usr/bin/pmset -a disablesleep 1, /usr/bin/pmset -a disablesleep 0, /usr/bin/pmset -g, /usr/bin/pmset sleepnow"
ADMIN_RULE="%admin ALL=(ALL) NOPASSWD: /usr/bin/pmset -a disablesleep 1, /usr/bin/pmset -a disablesleep 0, /usr/bin/pmset -g, /usr/bin/pmset sleepnow"

echo "=== Configuring Sudoers for 11Hopem AI Sleep Guard ==="
echo "Target User: ${TARGET_USER}"
echo "Target File: ${SUDOERS_FILE}"

TMP_FILE="$(mktemp /tmp/ai_sleep_guard_sudoers.XXXXXX)"
cat <<EOF > "${TMP_FILE}"
# Created by 11Hopem AI Sleep Guard
${RULE}
${ADMIN_RULE}
EOF
chmod 0440 "${TMP_FILE}"

if /usr/sbin/visudo -c -f "${TMP_FILE}"; then
    cp -f "${TMP_FILE}" "${SUDOERS_FILE}"
    chmod 0440 "${SUDOERS_FILE}"
    rm -f "${TMP_FILE}"
    echo "✓ Sudoers file installed successfully for ${TARGET_USER} and %admin!"
else
    echo "✗ Sudoers validation failed! Aborting for safety."
    rm -f "${TMP_FILE}"
    exit 1
fi

echo "✓ AI Sleep Guard can now manage clamshell / lid-close sleep assertions without password prompts."
