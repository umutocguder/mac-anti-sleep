<!-- Created by 11Hopem -->
# mac-anti-sleep (ai-sleep-guard)

<p align="center">
  <img src="assets/images/logo.svg" alt="mac-anti-sleep Logo" width="160" height="160" />
</p>

<p align="center">
  <b>Autonomous macOS Display & System Sleep Guard for Antigravity, Claude Code, and OpenAI Codex</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge&logo=apple" alt="Build Status" />
  <img src="https://img.shields.io/badge/Tests-100%25%20Passed-success?style=for-the-badge&logo=pytest" alt="Tests" />
  <img src="https://img.shields.io/badge/Platform-macOS%20Apple%20Silicon%20%26%20Intel-blue?style=for-the-badge&logo=apple" alt="Platform" />
  <img src="https://img.shields.io/badge/Thermal-Protected-red?style=for-the-badge&logo=apple" alt="Thermal Guard" />
  <img src="https://img.shields.io/badge/Firebase-hopem--software--cloud-orange?style=for-the-badge&logo=firebase" alt="Firebase" />
  <img src="https://img.shields.io/badge/License-11Hopem%20Proprietary-blueviolet?style=for-the-badge" alt="License" />
</p>

---

## 1. Project Title, Badges & Vision
`mac-anti-sleep` (`ai-sleep-guard`) is a specialized macOS system daemon that guarantees your Mac will **never sleep while AI agent prompts are running**, even if the laptop lid is closed. It natively monitors:
1. **Google Antigravity (Burda):** Active conversation turns, tool calls, and streaming responses in Antigravity IDE.
2. **Claude Code:** Prompts, shell commands, and subagent runs via native lifecycle hooks and process inspection.
3. **OpenAI Codex:** Active code generation, tool calls, and turns via SQLite WAL updates and notify wrappers.

When an AI prompt begins, the daemon immediately creates system and display power assertions (`caffeinate -d -i`) and low-level clamshell assertions (`pmset -a disablesleep 1`). Once all prompts conclude, it enforces a gentle **45-second cooldown buffer** before restoring macOS's default power-saving sleep timer (`pmset -a disablesleep 0`), allowing closed laptops to sleep immediately.

Crucially, it incorporates a **Thermal Safety Guard**: if CPU temperatures or thermal pressure reach dangerous levels (`NSProcessInfoThermalStateSerious` or `Critical`), it automatically halts active prompt processes (`SIGINT`), clears sleep assertions, sends an emergency desktop notification, and allows hardware to cool down.

---

## 2. Live Links & Project Registry
- **Private GitHub Repository:** [https://github.com/umutocguder/mac-anti-sleep](https://github.com/umutocguder/mac-anti-sleep)
- **Firebase Project ID:** `hopem-software-cloud`
- **Firestore Telemetry Collection:** `telemetry_logs`
- **Service Identifier:** `com.11hopem.ai-sleep-guard`
- **Official Brand Domain:** [https://11hopem.com](https://11hopem.com)

---

## 3. Real-World Operational Context
- **Target Workstation:** macOS Developer Environment running Antigravity IDE, Claude Code CLI, and Codex CLI.
- **Problem Solved:** When AI models execute long-running prompts, deep reasoning chains, or extensive multi-file tool invocations, the developer often steps away or closes the laptop lid. By default, closing the lid triggers hardware clamshell sleep, killing tasks prematurely.
- **Solution:** A zero-configuration, zero-dependency background LaunchAgent that manages both idle assertions and clamshell sleep settings, with hardware thermal protection to prevent overheating.

---

## 4. Key Features & Interactive Capabilities
- **Multi-Agent Active Prompt Tracking:**
  - **Antigravity:** Real-time read-only inspection of `~/.gemini/antigravity/conversation_summaries.db` for `CASCADE_RUN_STATUS_RUNNING` and `not_fully_idle = 1`.
  - **Claude Code:** Hooked into `UserPromptSubmit`, `PreToolUse`, `SubagentStart`, `Stop`, and `SessionEnd` in `~/.claude/settings.json`.
  - **OpenAI Codex:** Hooked into `notify` in `~/.codex/config.toml` alongside active SQLite WAL monitoring.
- **Clamshell (Lid-Closed) Sleep Guard:**
  - Automatically manages `pmset -a disablesleep 1` while prompts are executing.
  - Automatically restores `pmset -a disablesleep 0` when prompts finish and cooldown expires, so a closed MacBook sleeps naturally.
- **Thermal Safety Guard & Emergency Halt:**
  - Continuously monitors macOS thermal pressure using Apple's official `NSProcessInfo.thermalState` API.
  - If temperatures exceed safe thresholds (`Serious` or `Critical`), it immediately halts prompt processes, releases power assertions, posts an alert notification, and prevents thermal damage.
- **Zero-Dependency Core:** Built 100% on Python 3 standard library (`ctypes`, `sqlite3`, `subprocess`, `os`, `signal`, `urllib`).
- **macOS Native Caffeinate Integration:** Calls `/usr/bin/caffeinate -d -i` to create legitimate system assertions.
- **Intelligent 45s Cooldown Buffer:** Prevents flickering display power cycles between consecutive agent turns.
- **Rich Status CLI:** Terminal dashboard with ANSI color badges displaying live detector statuses, thermal state, and active PIDs.

---

## 5. Architecture, Tech Stack & Directory Tree
```
mac-anti-sleep/
├── README.md                          # Rich 10-section documentation
├── .gitignore                         # Strict exclusion rules
├── com.11hopem.ai-sleep-guard.plist    # macOS LaunchAgent definition
├── assets/
│   └── images/logo.svg                # 1:1 Vector brand mark
├── scripts/
│   ├── ai-sleep-guard                 # Main CLI launcher
│   ├── setup_sudo.sh                  # Sudoers configuration for pmset
│   ├── codex_notify.sh                # Codex notification bridge
│   ├── install.sh                     # Automated installer
│   └── uninstall.sh                   # Clean uninstaller
├── src/
│   ├── __init__.py
│   ├── cli.py                         # CLI argument dispatcher
│   ├── daemon.py                      # Continuous monitoring engine
│   ├── caffeinate_manager.py          # Caffeinate process & assertion lifecycle
│   ├── clamshell_manager.py           # Low-level pmset disablesleep manager
│   ├── thermal.py                     # NSProcessInfo thermal safety guard
│   ├── telemetry.py                   # Firestore & local audit logger
│   └── detectors/
│       ├── __init__.py
│       ├── base.py                    # Base signal & process utilities
│       ├── antigravity.py             # Antigravity SQLite detector
│       ├── claude.py                  # Claude Code hook & process detector
│       └── codex.py                   # Codex WAL & notify detector
├── tests/
│   ├── test_detectors.py              # Detector unit test suite
│   ├── test_caffeinate_manager.py     # Caffeinate manager test suite
│   ├── test_clamshell_manager.py      # Clamshell manager test suite
│   ├── test_thermal.py                # Thermal safety guard test suite
│   ├── test_telemetry.py              # Telemetry test suite
│   └── test_cli.py                    # CLI command test suite
└── data/
    └── telemetry_logs.jsonl           # Local audit event log
```

---

## 6. Security, Anti-Bot & Isolation Shield
- **100% Read-Only Database Queries:** Antigravity and Codex databases are queried using SQLite URI read-only immutable mode (`file:...db?mode=ro`) with 1.0-second timeouts, guaranteeing zero database locks or write conflicts.
- **Strict Sudoers Scope:** Only `pmset -a disablesleep` and `pmset sleepnow` are permitted in `/etc/sudoers.d/ai-sleep-guard` with `0440` permissions.
- **Local Data Custody:** Telemetry is written to local JSON Lines first before any network transmission.
- **Clean Signal Isolation:** Inter-process signals use secure user-owned directories in `~/.local/state/ai_sleep_guard/`.

---

## 7. Firebase Telemetry & Live Metrics
Every state change is captured locally in `data/telemetry_logs.jsonl` and mirrored to Cloud Firestore REST (`hopem-software-cloud`):
- `DAEMON_START`: Daemon initialization parameters.
- `CAFFEINATE_START`: Triggered when an AI prompt starts.
- `CAFFEINATE_STOP`: Triggered when prompts conclude and cooldown expires.
- `CLAMSHELL_SLEEP_ENABLE`: Lid-close sleep prevention enabled for active turn.
- `CLAMSHELL_SLEEP_DISABLE`: Lid-close sleep restored to default.
- `THERMAL_EMERGENCY_HALT`: High-priority alert when temperature threshold is exceeded.

---

## 8. Autonomous Data Backup
- Local audit logs are preserved in `data/telemetry_logs.jsonl`.
- LaunchAgent stdout and stderr logs are recorded in `/Users/umut/Library/Logs/mac-anti-sleep/`.

---

## 9. Installation, Testing & Quality Assurance
### Quick Installation
```bash
cd /Users/umut/mycodespaces/mac-anti-sleep
bash scripts/install.sh
```

### Enable Lid-Close Sleep Prevention (One-Time Setup)
```bash
ai-sleep-guard setup-sudo
# Or execute:
bash scripts/setup_sudo.sh
```

### Checking Live Status & Thermal Diagnostics
```bash
ai-sleep-guard status
ai-sleep-guard thermal
```

### Running Automated Tests
```bash
python3 -m unittest discover -s tests -v
```

### Manual Overrides
```bash
ai-sleep-guard on       # Force system awake
ai-sleep-guard off      # Restore normal sleep
ai-sleep-guard wrap npm run build   # Keep system awake while command runs
```

---

## 10. 11Hopem Attribution & Legal
Created by [11Hopem](https://11hopem.com).
Copyright (c) 2026 11Hopem. All rights reserved.
Licensed under 11Hopem Proprietary License.
