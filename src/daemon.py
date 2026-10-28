# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Background Daemon Engine for mac-anti-sleep.
Continuously coordinates detectors, manages caffeinate assertion, and persists live status.
"""

import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Any

from .caffeinate_manager import CaffeinateManager
from .detectors import (
    ensure_signal_dir,
    is_signal_active,
    check_antigravity_activity,
    check_claude_activity,
    check_codex_activity
)
from .telemetry import record_event

logger = logging.getLogger(__name__)

STATUS_FILE = "/tmp/ai_sleep_guard/status.json"
PID_FILE = "/tmp/ai_sleep_guard/daemon.pid"


class SleepGuardDaemon:
    """Daemon process continuously keeping the display awake while AI prompts run."""

    def __init__(self, poll_interval: float = 2.5, cooldown_seconds: float = 45.0):
        self.poll_interval = poll_interval
        self.cooldown_seconds = cooldown_seconds
        self.manager = CaffeinateManager(default_cooldown_seconds=cooldown_seconds)
        self.running = False

    def handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handles graceful termination signals."""
        logger.info(f"Received signal {signum}. Shutting down SleepGuardDaemon...")
        self.running = False
        self.manager.stop()
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except OSError:
            pass
        sys.exit(0)

    def write_pid(self) -> None:
        """Writes current process PID to state file."""
        ensure_signal_dir()
        try:
            with open(PID_FILE, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except OSError as e:
            logger.error(f"Failed to write PID file: {e}")

    def write_status(self, current_state: Dict[str, Any]) -> None:
        """Saves current diagnostics to status.json for instant CLI lookup."""
        ensure_signal_dir()
        temp_status = f"{STATUS_FILE}.tmp"
        try:
            with open(temp_status, "w", encoding="utf-8") as f:
                json.dump(current_state, f, indent=2)
            os.replace(temp_status, STATUS_FILE)
        except OSError as e:
            logger.debug(f"Failed to update status.json: {e}")

    def run(self) -> None:
        """Starts the main daemon polling loop."""
        self.running = True
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

        self.write_pid()
        logger.info("SleepGuardDaemon started successfully.")
        record_event("DAEMON_START", {
            "poll_interval": self.poll_interval,
            "cooldown_seconds": self.cooldown_seconds
        }, status="SUCCESS")

        while self.running:
            try:
                # 1. Run all three agent detectors
                ag_active, ag_det = check_antigravity_activity()
                cl_active, cl_det = check_claude_activity()
                cx_active, cx_det = check_codex_activity()

                # 2. Check for manual override signal
                manual_active, manual_age = is_signal_active("manual", max_age_seconds=7200.0)

                active_agents = []
                active_reasons = []

                if ag_active:
                    active_agents.append("antigravity")
                    active_reasons.append(f"Antigravity: {ag_det.get('reason')}")
                if cl_active:
                    active_agents.append("claude")
                    active_reasons.append(f"Claude: {cl_det.get('reason')}")
                if cx_active:
                    active_agents.append("codex")
                    active_reasons.append(f"Codex: {cx_det.get('reason')}")
                if manual_active:
                    active_agents.append("manual_override")
                    active_reasons.append("Manual override active")

                any_active = len(active_agents) > 0
                combined_reason = ", ".join(active_reasons) if active_reasons else "All agents idle"

                # 3. Manage power assertion via CaffeinateManager
                if any_active:
                    self.manager.touch(reason=combined_reason)
                else:
                    if not self.manager.should_stay_awake(
                        is_active_now=False, cooldown_seconds=self.cooldown_seconds
                    ):
                        if self.manager.is_running():
                            self.manager.stop()

                # 4. Snapshot current state for CLI inspection
                caff_status = self.manager.get_status()
                state_snapshot = {
                    "timestamp": time.time(),
                    "daemon_pid": os.getpid(),
                    "any_active": any_active,
                    "active_agents": active_agents,
                    "reason": combined_reason,
                    "caffeinate": caff_status,
                    "detectors": {
                        "antigravity": ag_det,
                        "claude": cl_det,
                        "codex": cx_det,
                        "manual": {"active": manual_active, "age": manual_age}
                    }
                }
                self.write_status(state_snapshot)

            except Exception as loop_err:
                logger.error(f"Error in daemon loop: {loop_err}", exc_info=True)

            time.sleep(self.poll_interval)
