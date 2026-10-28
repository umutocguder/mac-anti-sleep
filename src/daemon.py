# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Background Daemon Engine for mac-anti-sleep.
Continuously coordinates agent detectors, manages caffeinate and clamshell assertions,
monitors thermal safety, and persists live status.
"""

import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Any

from src.caffeinate_manager import CaffeinateManager
from src.clamshell_manager import ClamshellManager
from src.detectors import (
    ensure_signal_dir,
    is_signal_active,
    check_antigravity_activity,
    check_claude_activity,
    check_codex_activity
)
from src.telemetry import record_event
from src.thermal import ThermalGuard, THERMAL_STATE_FAIR

logger = logging.getLogger(__name__)

STATE_DIR = os.path.expanduser("~/.local/state/ai_sleep_guard")
STATUS_FILE = os.path.join(STATE_DIR, "status.json")
PID_FILE = os.path.join(STATE_DIR, "daemon.pid")


class SleepGuardDaemon:
    """Daemon process continuously keeping the system awake while AI prompts run."""

    def __init__(
        self,
        poll_interval: float = 2.5,
        cooldown_seconds: float = 45.0,
        enable_clamshell: bool = True
    ):
        self.poll_interval = poll_interval
        self.cooldown_seconds = cooldown_seconds
        self.enable_clamshell = enable_clamshell

        self.caffeinate_manager = CaffeinateManager(default_cooldown_seconds=cooldown_seconds)
        self.clamshell_manager = ClamshellManager(auto_restore=True)
        self.thermal_guard = ThermalGuard()
        self.running = False

    def handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handles graceful termination signals."""
        logger.info(f"Received signal {signum}. Shutting down SleepGuardDaemon...")
        self.running = False
        self.caffeinate_manager.stop()
        self.clamshell_manager.restore_defaults()
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
            "cooldown_seconds": self.cooldown_seconds,
            "enable_clamshell": self.enable_clamshell
        }, status="SUCCESS")

        while self.running:
            try:
                # 1. Thermal Safety Check
                thermal_status = self.thermal_guard.get_thermal_status()
                if thermal_status.get("is_overheating"):
                    logger.warning("Thermal threshold exceeded! Halting active prompts and releasing sleep assertions.")
                    self.thermal_guard.execute_emergency_halt(reason="mac_hardware_overheat")
                    self.caffeinate_manager.stop()
                    self.clamshell_manager.set_clamshell_sleep_prevention(False)

                    # Snapshot emergency state
                    state_snapshot = {
                        "timestamp": time.time(),
                        "daemon_pid": os.getpid(),
                        "emergency_thermal_halt": True,
                        "thermal": thermal_status,
                        "caffeinate": self.caffeinate_manager.get_status(),
                        "clamshell": self.clamshell_manager.get_status()
                    }
                    self.write_status(state_snapshot)
                    time.sleep(self.poll_interval)
                    continue

                # Check if recovering from a thermal lockout
                if thermal_status.get("lockout_active"):
                    if thermal_status.get("thermal_state_code", 0) <= THERMAL_STATE_FAIR:
                        self.thermal_guard.clear_thermal_lockout()
                    else:
                        # Continue waiting for temperature to drop
                        time.sleep(self.poll_interval)
                        continue

                # 2. Run all three agent detectors
                ag_active, ag_det = check_antigravity_activity()
                cl_active, cl_det = check_claude_activity()
                cx_active, cx_det = check_codex_activity()

                # 3. Check for manual override signal
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

                # 4. Manage power assertions (caffeinate + clamshell lid-close prevention)
                if any_active:
                    self.caffeinate_manager.touch(reason=combined_reason)
                    if self.enable_clamshell:
                        self.clamshell_manager.set_clamshell_sleep_prevention(True)
                else:
                    if not self.caffeinate_manager.should_stay_awake(
                        is_active_now=False, cooldown_seconds=self.cooldown_seconds
                    ):
                        if self.caffeinate_manager.is_running():
                            self.caffeinate_manager.stop()
                        if self.clamshell_manager.clamshell_active:
                            # Prompt finished & cooldown passed: Restore normal sleep!
                            # If laptop lid is currently closed, macOS will sleep immediately.
                            self.clamshell_manager.set_clamshell_sleep_prevention(False)

                # 5. Snapshot current state for CLI inspection
                caff_status = self.caffeinate_manager.get_status()
                clam_status = self.clamshell_manager.get_status()
                state_snapshot = {
                    "timestamp": time.time(),
                    "daemon_pid": os.getpid(),
                    "any_active": any_active,
                    "active_agents": active_agents,
                    "reason": combined_reason,
                    "caffeinate": caff_status,
                    "clamshell": clam_status,
                    "thermal": thermal_status,
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
