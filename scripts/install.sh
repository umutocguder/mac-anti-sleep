#!/bin/bash
# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Installing 11Hopem AI Sleep Guard ==="

# 1. Create Directories
mkdir -p "${HOME}/Library/Logs/mac-anti-sleep"
mkdir -p "${HOME}/.local/bin"
mkdir -p "${HOME}/Library/LaunchAgents"

# 2. Make scripts executable
chmod +x "${PROJECT_ROOT}/scripts/ai-sleep-guard"
chmod +x "${PROJECT_ROOT}/scripts/codex_notify.sh"

# 3. Create symlink in ~/.local/bin
ln -sf "${PROJECT_ROOT}/scripts/ai-sleep-guard" "${HOME}/.local/bin/ai-sleep-guard"
echo "✓ Symlinked ai-sleep-guard to ${HOME}/.local/bin/ai-sleep-guard"

# 4. Configure Claude Code hooks in ~/.claude/settings.json
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"
if [ -f "${CLAUDE_SETTINGS}" ]; then
    /usr/bin/python3 -c "
import json

path = '${CLAUDE_SETTINGS}'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

hooks = data.get('hooks', {})
hooks['UserPromptSubmit'] = [{'hooks': [{'type': 'command', 'command': 'ai-sleep-guard ping claude'}]}]
hooks['PreToolUse'] = [{'hooks': [{'type': 'command', 'command': 'ai-sleep-guard ping claude'}]}]
hooks['SubagentStart'] = [{'hooks': [{'type': 'command', 'command': 'ai-sleep-guard ping claude'}]}]
hooks['Stop'] = [{'hooks': [{'type': 'command', 'command': 'ai-sleep-guard done claude'}]}]
hooks['SessionEnd'] = [{'hooks': [{'type': 'command', 'command': 'ai-sleep-guard done claude'}]}]

data['hooks'] = hooks

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
print('✓ Successfully configured Claude Code lifecycle hooks in ~/.claude/settings.json')
"
fi

# 5. Configure Codex notify wrapper in ~/.codex/config.toml
CODEX_CONFIG="${HOME}/.codex/config.toml"
if [ -f "${CODEX_CONFIG}" ]; then
    /usr/bin/python3 -c "
path = '${CODEX_CONFIG}'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

notify_line = 'notify = [\"${PROJECT_ROOT}/scripts/codex_notify.sh\", \"turn-ended\"]'

# Replace existing notify or add it
import re
if re.search(r'^notify\s*=', content, flags=re.MULTILINE):
    content = re.sub(r'^notify\s*=.*$', notify_line, content, flags=re.MULTILINE)
else:
    content = notify_line + '\n' + content

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('✓ Successfully configured Codex notify in ~/.codex/config.toml')
"
fi

# 6. Install LaunchAgent
PLIST_SRC="${PROJECT_ROOT}/com.11hopem.ai-sleep-guard.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.11hopem.ai-sleep-guard.plist"
cp -f "${PLIST_SRC}" "${PLIST_DST}"

# Unload previous instance if running
launchctl bootout "gui/$(id -u)/com.11hopem.ai-sleep-guard" 2>/dev/null || launchctl unload "${PLIST_DST}" 2>/dev/null || true

# Bootstrap / load new instance
launchctl bootstrap "gui/$(id -u)" "${PLIST_DST}" 2>/dev/null || launchctl load -w "${PLIST_DST}"
echo "✓ Loaded LaunchAgent: com.11hopem.ai-sleep-guard"

# 7. Check status
sleep 1
"${HOME}/.local/bin/ai-sleep-guard" status

echo "=== 11Hopem AI Sleep Guard successfully installed and running! ==="
