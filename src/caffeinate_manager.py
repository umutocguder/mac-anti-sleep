# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Caffeinate Process and macOS Power Assertion Manager.
Handles display (-d) and system idle (-i) sleep prevention with graceful cooldown.
"""

import atexit
import logging
import os
import signal
import subprocess
import time
from typing import Optional, Dict, Any

from src.telemetry import record_event

logger = logging.getLogger(__name__)


class CaffeinateManager:
    """Manages the lifecycle of the caffeinate background process."""

    def __init__(self, default_cooldown_seconds: float = 45.0):
        self.default_cooldown_seconds = default_cooldown_seconds
        self.process: Optional[subprocess.Popen] = None
        self.last_active_time: float = 0.0
        self.last_reason: str = "init"
        self.start_time: Optional[float] = None

        # Clean up caffeinate child process on exit
        atexit.register(self.stop)

    def is_running(self) -> bool:
        """Checks if our managed caffeinate process is currently alive."""
        if self.process is not None:
            if self.process.poll() is None:
                return True
            self.process = None
        return False

    def start(self, reason: str = "prompt_active") -> bool:
        """
        Starts caffeinate with display (-d) and system idle (-i) sleep prevention.
        """
        self.last_active_time = time.time()
        self.last_reason = reason

        if self.is_running():
            return True

        try:
            # -d: prevents display sleep
            # -i: prevents system idle sleep
            self.process = subprocess.Popen(
                ["/usr/bin/caffeinate", "-d", "-i"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            self.start_time = time.time()
            logger.info(f"Caffeinate spawned with PID {self.process.pid} (reason: {reason})")
            record_event("CAFFEINATE_START", {
                "pid": self.process.pid,
                "reason": reason,
                "flags": ["-d", "-i"]
            }, status="SUCCESS")
            return True
        except Exception as e:
            logger.error(f"Failed to spawn caffeinate: {e}")
            record_event("CAFFEINATE_ERROR", {"error": str(e)}, status="ERROR")
            self.process = None
            return False

    def stop(self) -> bool:
        """Terminates the caffeinate process cleanly."""
        if self.process is None:
            return True

        pid = self.process.pid
        duration = time.time() - self.start_time if self.start_time else 0.0
        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logger.info(f"Caffeinate PID {pid} stopped (duration: {duration:.1f}s)")
            record_event("CAFFEINATE_STOP", {
                "pid": pid,
                "active_duration_seconds": round(duration, 2),
                "last_reason": self.last_reason
            }, status="INFO")
        except Exception as e:
            logger.error(f"Error terminating caffeinate PID {pid}: {e}")
        finally:
            self.process = None
            self.start_time = None

        return True

    def touch(self, reason: str = "keepalive") -> None:
        """Updates the active timestamp and ensures caffeinate is running."""
        self.last_active_time = time.time()
        self.last_reason = reason
        if not self.is_running():
            self.start(reason=reason)

    def should_stay_awake(self, is_active_now: bool, cooldown_seconds: Optional[float] = None) -> bool:
        """
        Determines whether sleep prevention should remain active based on
        current agent activity or the cooldown buffer.
        """
        if is_active_now:
            return True
        cooldown = cooldown_seconds if cooldown_seconds is not None else self.default_cooldown_seconds
        elapsed_since_active = time.time() - self.last_active_time
        return elapsed_since_active < cooldown

    def get_cooldown_remaining(self, cooldown_seconds: Optional[float] = None) -> float:
        """Returns the number of seconds left before cooldown expires."""
        cooldown = cooldown_seconds if cooldown_seconds is not None else self.default_cooldown_seconds
        elapsed = time.time() - self.last_active_time
        remaining = cooldown - elapsed
        return max(0.0, remaining)

    def get_status(self) -> Dict[str, Any]:
        """Returns diagnostic status of the caffeinate manager."""
        running = self.is_running()
        duration = (time.time() - self.start_time) if (running and self.start_time) else 0.0
        cooldown_left = self.get_cooldown_remaining()
        return {
            "caffeinate_running": running,
            "pid": self.process.pid if running and self.process else None,
            "active_duration_seconds": round(duration, 1),
            "cooldown_remaining_seconds": round(cooldown_left, 1),
            "last_active_reason": self.last_reason,
            "system_display_assertion": self.check_system_display_assertion()
        }

    @staticmethod
    def check_system_display_assertion() -> bool:
        """Verifies if PreventUserIdleDisplaySleep is currently active on macOS."""
        try:
            res = subprocess.run(
                ["/usr/bin/pmset", "-g", "assertions"],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            for line in res.stdout.splitlines():
                if "PreventUserIdleDisplaySleep" in line and "1" in line:
                    return True
        except Exception:
            pass
        return False
