# WORKLOG — mac-anti-sleep

## 2026-10-28 22:57 — Initial Autonomous System Architecture & Implementation

### Task & Purpose
Implement an autonomous, multi-agent macOS display and system sleep prevention service (`ai-sleep-guard`) that prevents the Mac display from sleeping whenever prompts or tasks are actively executing in Antigravity (Gemini), Claude Code, or OpenAI Codex.

### Technical Decisions & Architecture
1. **Multi-Agent Detection Architecture:**
   - **Antigravity (Burda):** Implemented read-only SQLite queries against `~/.gemini/antigravity/conversation_summaries.db` inspecting `CASCADE_RUN_STATUS_RUNNING` and `not_fully_idle = 1` within active time windows, combined with brain transcript write monitoring.
   - **Claude Code:** Configured native hooks in `~/.claude/settings.json` (`UserPromptSubmit`, `PreToolUse`, `SubagentStart`, `Stop`, `SessionEnd`) to signal prompt start and completion, backed by child process inspection.
   - **OpenAI Codex:** Configured `notify` in `~/.codex/config.toml` via `scripts/codex_notify.sh` combined with SQLite WAL monitoring (`logs_2.sqlite-wal`, `state_5.sqlite-wal`).
2. **Caffeinate Lifecycle & Cooldown:**
   - Implemented `CaffeinateManager` wrapping `/usr/bin/caffeinate -d -i` with a 45-second graceful cooldown buffer to eliminate screen flickering between rapid back-and-forth prompt turns.
3. **LaunchAgent Integration:**
   - Created `~/Library/LaunchAgents/com.11hopem.ai-sleep-guard.plist` with `RunAtLoad` and `KeepAlive` for persistent zero-configuration operation on macOS.
4. **Telemetry & Custody:**
   - Integrated local JSONL auditing in `data/telemetry_logs.jsonl` with non-blocking Cloud Firestore REST ingestion (`hopem-software-cloud`).

### Affected Files & Components
- [`src/detectors/base.py`](file:///Users/umut/mycodespaces/mac-anti-sleep/src/detectors/base.py) — Common signals and process checks.
- [`src/detectors/antigravity.py`](file:///Users/umut/mycodespaces/mac-anti-sleep/src/detectors/antigravity.py) — Antigravity prompt state detector.
- [`src/detectors/claude.py`](file:///Users/umut/mycodespaces/mac-anti-sleep/src/detectors/claude.py) — Claude Code hook and process detector.
- [`src/detectors/codex.py`](file:///Users/umut/mycodespaces/mac-anti-sleep/src/detectors/codex.py) — Codex WAL and turn detector.
- [`src/caffeinate_manager.py`](file:///Users/umut/mycodespaces/mac-anti-sleep/src/caffeinate_manager.py) — Power assertion controller.
- [`src/daemon.py`](file:///Users/umut/mycodespaces/mac-anti-sleep/src/daemon.py) — Continuous coordination loop.
- [`src/cli.py`](file:///Users/umut/mycodespaces/mac-anti-sleep/src/cli.py) — CLI dispatcher (`ai-sleep-guard`).
- [`src/telemetry.py`](file:///Users/umut/mycodespaces/mac-anti-sleep/src/telemetry.py) — Cloud Firestore and local audit logger.
- [`scripts/install.sh`](file:///Users/umut/mycodespaces/mac-anti-sleep/scripts/install.sh) — Automated installer.
- [`scripts/uninstall.sh`](file:///Users/umut/mycodespaces/mac-anti-sleep/scripts/uninstall.sh) — Clean uninstaller.
- [`scripts/codex_notify.sh`](file:///Users/umut/mycodespaces/mac-anti-sleep/scripts/codex_notify.sh) — Codex notification wrapper.
- [`tests/`](file:///Users/umut/mycodespaces/mac-anti-sleep/tests/) — 11 automated unit tests across all components.

### Current State & Verification
- Unit test suite executed via `python3 -m unittest discover -s tests -v`: **11 tests passed (100% SUCCESS)**.
- Display assertion successfully confirmed with `pmset -g assertions`.

### Next Steps
- Run `bash scripts/install.sh` to install LaunchAgent, register Claude and Codex hooks, and activate live system protection.
- Push to private GitHub repository (`umutocguder/mac-anti-sleep`) on `dev` and `master` branches.
- Update `/Users/umut/ai-context/` documentation.
