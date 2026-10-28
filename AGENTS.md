# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

# AGENTS.md — mac-anti-sleep System Architecture & Development Guidelines

Welcome to `mac-anti-sleep` (CLI: `ai-sleep-guard`), the autonomous macOS background service that prevents display and system sleep while AI agents (Antigravity/Gemini, Claude Code, and OpenAI Codex) are actively executing prompts, tasks, or subagents.

---

## 1. Project Overview & Architecture
- **Language / Runtime:** Python 3.10+ (Standard Library Only — Zero external package dependencies).
- **Service Type:** macOS LaunchAgent (`~/Library/LaunchAgents/com.11hopem.ai-sleep-guard.plist`).
- **Target OS:** macOS (Apple Silicon & Intel) using built-in `/usr/bin/caffeinate` and `/usr/bin/pmset`.
- **Primary CLI Command:** `ai-sleep-guard` (symlinked into `~/.local/bin/ai-sleep-guard`).
- **Telemetry & Local Data Custody:** Local JSON Lines audit log (`data/telemetry_logs.jsonl`) + non-blocking Cloud Firestore REST stream (`hopem-software-cloud` project).

### Detector Strategy
1. **Antigravity (Burda):**
   - Querying `~/.gemini/antigravity/conversation_summaries.db` in read-only mode for `CASCADE_RUN_STATUS_RUNNING` or `not_fully_idle = 1`.
   - Monitoring live transcript updates in `~/.gemini/antigravity/brain/*/transcript.jsonl`.
2. **Claude Code:**
   - Native lifecycle hooks in `~/.claude/settings.json` (`UserPromptSubmit`, `PreToolUse`, `SubagentStart`, `Stop`, `SessionEnd`).
   - Process inspection and child command execution tracking.
3. **OpenAI Codex:**
   - Turn notification wrapper in `~/.codex/config.toml` via `scripts/codex_notify.sh`.
   - SQLite WAL file updates in `~/.codex/logs_2.sqlite-wal` and `~/.codex/state_5.sqlite-wal`.
4. **Caffeinate Manager:**
   - Controls `/usr/bin/caffeinate -d -i`.
   - Enforces a 45-second graceful cooldown before releasing sleep assertion when prompts finish.

---

## 2. Directory Tree
```
mac-anti-sleep/
├── AGENTS.md                          # Architecture and development rules
├── CLAUDE.md                          # Points to @AGENTS.md
├── WORKLOG.md                         # AI Handoff Ready operational log
├── README.md                          # Rich 10-section documentation
├── .gitignore                         # Strict exclusion rules
├── com.11hopem.ai-sleep-guard.plist    # macOS LaunchAgent specification
├── assets/
│   └── images/logo.svg                # Dedicated SVG vector logo
├── scripts/
│   ├── ai-sleep-guard                 # Executable CLI launcher
│   ├── codex_notify.sh                # Codex notification wrapper
│   ├── install.sh                     # Automated installation script
│   └── uninstall.sh                   # Clean uninstaller
├── src/
│   ├── __init__.py
│   ├── cli.py                         # CLI subcommands (status, ping, done, on, off, wrap, daemon)
│   ├── daemon.py                      # Core background loop and state writer
│   ├── caffeinate_manager.py          # Subprocess and assertion manager
│   ├── telemetry.py                   # Local audit + Firestore REST telemetry
│   └── detectors/
│       ├── __init__.py
│       ├── base.py                    # Shared signal & process utilities
│       ├── antigravity.py             # Antigravity activity detector
│       ├── claude.py                  # Claude Code activity detector
│       └── codex.py                   # Codex activity detector
├── tests/
│   ├── test_detectors.py              # Unit tests for detectors
│   ├── test_caffeinate_manager.py     # Unit tests for caffeinate manager
│   ├── test_telemetry.py              # Unit tests for telemetry
│   └── test_cli.py                    # Unit tests for CLI parsing
└── data/                              # Local JSONL telemetry records
```

---

## 3. Essential Commands
- **Run Unit Tests:** `python3 -m unittest discover -s tests -v`
- **Inspect Live Status:** `ai-sleep-guard status`
- **Install & Bootstrap Daemon:** `bash scripts/install.sh`
- **Uninstall Service:** `bash scripts/uninstall.sh`
- **Manual Force Awake:** `ai-sleep-guard on`
- **Release Force Awake:** `ai-sleep-guard off`

---

## 4. Mandatory Development Standards
- **Zero Turkish in Code:** All source code, docstrings, variable names, log output, and test assertions must be 100% English.
- **Git Branch Model:** `dev` (development / UAT) and `master` (production release).
- **Commit Identity:** Umut Öçgüder <umutocgdr@gmail.com>.
