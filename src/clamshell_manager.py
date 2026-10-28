# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Clamshell (Lid-Closed) Power Assertion and Sleep Manager.
Controls low-level macOS sleep settings via pmset to prevent hardware sleep
while laptop lid is closed during active AI prompts, and immediately restores
natural sleep when tasks complete.
"""

import atexit
import logging
import subprocess
from typing import Dict, Any, Optional

from src.telemetry import record_event

logger = logging.getLogger(__name__)


class ClamshellManager:
    """Manages low-level macOS clamshell sleep settings via pmset."""

    def __init__(self):
        self.clamshell_active: bool = False
        self._sudo_available: Optional[bool] = None

        # Clean up low-level assertion on process shutdown
        atexit.register(self.restore_defaults)

    def can_manage_clamshell(self) -> bool:
        """Checks if passwordless sudo access for pmset is available."""
        try:
            res = subprocess.run(
                ["sudo", "-n", "/usr/bin/pmset", "-g"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0
            )
            self._sudo_available = (res.returncode == 0)
            return self._sudo_available
        except Exception:
            self._sudo_available = False
            return False

    @staticmethod
    def is_clamshell_sleep_disabled() -> bool:
        """
        Inspects live system power settings to check if SleepDisabled is currently 1.
        """
        try:
            res = subprocess.run(
                ["/usr/bin/pmset", "-g"],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            for line in res.stdout.splitlines():
                line_clean = line.strip().lower()
                if "sleepdisabled" in line_clean and "1" in line_clean:
                    return True
        except Exception:
            pass
        return False

    def set_clamshell_sleep_prevention(self, enable: bool) -> bool:
        """
        Enables or disables sleep prevention when laptop lid is closed.

        :param enable: True to prevent sleep when lid is closed, False to restore normal sleep.
        :return: True if command executed successfully.
        """
        val = 1 if enable else 0

        # Avoid redundant calls if state is already desired
        if self.clamshell_active == enable and self.is_clamshell_sleep_disabled() == enable:
            return True

        try:
            res = subprocess.run(
                ["sudo", "-n", "/usr/bin/pmset", "-a", "disablesleep", str(val)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3.0
            )
            if res.returncode == 0:
                self.clamshell_active = enable
                action_name = "ENABLE" if enable else "DISABLE"
                logger.info(f"Clamshell sleep prevention {action_name}D (disablesleep {val})")
                record_event(f"CLAMSHELL_SLEEP_{action_name}", {"disablesleep": val}, status="SUCCESS")
                return True
            else:
                err_msg = res.stderr.strip()
                logger.debug(f"Could not change disablesleep to {val} (sudo required?): {err_msg}")
                return False
        except Exception as e:
            logger.debug(f"Failed to execute pmset disablesleep: {e}")
            return False

    def restore_defaults(self) -> None:
        """Restores normal sleep settings before shutdown."""
        if self.clamshell_active or self.is_clamshell_sleep_disabled():
            try:
                subprocess.run(
                    ["sudo", "-n", "/usr/bin/pmset", "-a", "disablesleep", "0"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2.0
                )
                self.clamshell_active = False
                logger.info("Restored default sleep behavior (disablesleep 0).")
            except Exception:
                pass

    @staticmethod
    def trigger_immediate_sleep() -> bool:
        """Triggers immediate system sleep via pmset or AppleScript."""
        try:
            res = subprocess.run(
                ["/usr/bin/pmset", "sleepnow"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0
            )
            return res.returncode == 0
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """Returns diagnostic status of clamshell sleep manager."""
        can_sudo = self.can_manage_clamshell()
        is_disabled = self.is_clamshell_sleep_disabled()
        return {
            "clamshell_preventing_sleep": is_disabled,
            "sudoers_configured": can_sudo,
            "managed_state": self.clamshell_active
        }
