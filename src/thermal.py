# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Thermal Safety Guard for mac-anti-sleep.
Continuously monitors macOS thermal pressure using Apple's NSProcessInfo thermalState API
and pmset thermal metrics. Triggers emergency prompt halting and power release when
hardware temperatures reach dangerous thresholds.
"""

import ctypes
import ctypes.util
import logging
import os
import signal
import subprocess
import time
from typing import Dict, Any, List, Optional, Tuple

from src.detectors.base import get_process_pids, clear_signal
from src.telemetry import record_event

logger = logging.getLogger(__name__)

# Apple NSProcessInfoThermalState enum values
THERMAL_STATE_NOMINAL = 0
THERMAL_STATE_FAIR = 1
THERMAL_STATE_SERIOUS = 2
THERMAL_STATE_CRITICAL = 3

THERMAL_STATE_NAMES = {
    THERMAL_STATE_NOMINAL: "Nominal",
    THERMAL_STATE_FAIR: "Fair",
    THERMAL_STATE_SERIOUS: "Serious",
    THERMAL_STATE_CRITICAL: "Critical"
}

STATE_DIR = os.path.expanduser("~/.local/state/ai_sleep_guard")
THERMAL_LOCKOUT_FILE = os.path.join(STATE_DIR, "thermal_emergency.lock")


class ThermalGuard:
    """Monitors system thermal pressure and executes emergency halts if hardware overheats."""

    def __init__(self, halt_threshold_code: int = THERMAL_STATE_SERIOUS):
        """
        :param halt_threshold_code: Thermal state code at or above which an emergency halt is triggered.
                                     Default: THERMAL_STATE_SERIOUS (2).
        """
        self.halt_threshold_code = halt_threshold_code
        self._objc_available = False
        self._msg_send_id = None
        self._msg_send_long = None
        self._ns_process_info = None
        self._sel_process_info = None
        self._sel_thermal_state = None
        self._init_objc()

    def _init_objc(self) -> None:
        """Initializes macOS ObjC runtime bindings for NSProcessInfo."""
        try:
            libobjc_path = ctypes.util.find_library("objc")
            if not libobjc_path:
                logger.warning("Could not find libobjc; NSProcessInfo thermal monitoring disabled.")
                return

            libobjc = ctypes.cdll.LoadLibrary(libobjc_path)
            libobjc.objc_getClass.restype = ctypes.c_void_p
            libobjc.objc_getClass.argtypes = [ctypes.c_char_p]
            libobjc.sel_registerName.restype = ctypes.c_void_p
            libobjc.sel_registerName.argtypes = [ctypes.c_char_p]

            # ARM64 and x86_64 safe casting for objc_msgSend
            self._msg_send_id = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
                ("objc_msgSend", libobjc)
            )
            self._msg_send_long = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p)(
                ("objc_msgSend", libobjc)
            )

            self._ns_process_info = libobjc.objc_getClass(b"NSProcessInfo")
            self._sel_process_info = libobjc.sel_registerName(b"processInfo")
            self._sel_thermal_state = libobjc.sel_registerName(b"thermalState")
            self._objc_available = True
        except Exception as e:
            logger.warning(f"Failed to initialize ObjC bindings for thermal monitoring: {e}")
            self._objc_available = False

    def query_ns_thermal_state(self) -> Tuple[int, str]:
        """Queries Apple's NSProcessInfo thermalState directly via ObjC runtime."""
        if not self._objc_available:
            return THERMAL_STATE_NOMINAL, "Unknown"

        try:
            process_info = self._msg_send_id(self._ns_process_info, self._sel_process_info)
            if not process_info:
                return THERMAL_STATE_NOMINAL, "Unknown"
            state_code = int(self._msg_send_long(process_info, self._sel_thermal_state))
            state_name = THERMAL_STATE_NAMES.get(state_code, f"State_{state_code}")
            return state_code, state_name
        except Exception as e:
            logger.debug(f"Error querying NSProcessInfo thermalState: {e}")
            return THERMAL_STATE_NOMINAL, "Error"

    @staticmethod
    def query_pmset_thermal() -> Dict[str, Any]:
        """Parses /usr/bin/pmset -g therm output for CPU speed limits or thermal warnings."""
        result: Dict[str, Any] = {
            "cpu_speed_limit": None,
            "has_thermal_warning": False,
            "raw_output": ""
        }
        try:
            res = subprocess.run(
                ["/usr/bin/pmset", "-g", "therm"],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            output = res.stdout.strip()
            result["raw_output"] = output

            for line in output.splitlines():
                line_lower = line.lower()
                if "cpu_speed_limit" in line_lower:
                    parts = line.split("=")
                    if len(parts) >= 2:
                        try:
                            result["cpu_speed_limit"] = int(parts[1].strip())
                        except ValueError:
                            pass
                if "thermal warning" in line_lower and "no thermal warning" not in line_lower:
                    result["has_thermal_warning"] = True
        except Exception as e:
            logger.debug(f"Failed to query pmset therm: {e}")

        return result

    def get_thermal_status(self) -> Dict[str, Any]:
        """Returns comprehensive thermal diagnostics."""
        state_code, state_name = self.query_ns_thermal_state()
        pmset_data = self.query_pmset_thermal()
        is_overheating = state_code >= self.halt_threshold_code

        # Check if CPU speed is heavily throttled (< 70%) by thermal manager
        cpu_throttled = pmset_data["cpu_speed_limit"] is not None and pmset_data["cpu_speed_limit"] < 70
        if cpu_throttled or pmset_data["has_thermal_warning"]:
            is_overheating = True

        return {
            "thermal_state_code": state_code,
            "thermal_state_name": state_name,
            "is_overheating": is_overheating,
            "is_critical": state_code >= THERMAL_STATE_CRITICAL,
            "cpu_speed_limit": pmset_data.get("cpu_speed_limit"),
            "pmset_warning": pmset_data.get("has_thermal_warning", False),
            "lockout_active": os.path.exists(THERMAL_LOCKOUT_FILE)
        }

    @staticmethod
    def notify_user(title: str, message: str) -> None:
        """Sends native macOS desktop notification via osascript."""
        try:
            script = f'display notification "{message}" with title "{title}" subtitle "🔴 Thermal Protection"'
            subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0
            )
        except Exception as e:
            logger.debug(f"Failed to post desktop notification: {e}")

    def execute_emergency_halt(self, reason: str = "high_thermal_pressure") -> Dict[str, Any]:
        """
        Executes immediate emergency shutdown of active prompts:
        1. Halts active agent processes (SIGINT/SIGTERM) to drop CPU load instantly.
        2. Clears agent signals.
        3. Creates a thermal lockout flag.
        4. Sends high-priority macOS desktop notification.
        5. Records emergency alert in telemetry.
        """
        logger.warning(f"EMERGENCY THERMAL HALT TRIGGERED: {reason}")
        halted_pids: List[int] = []

        # 1. Identify active agent processes
        agent_names = ["claude", "codex"]
        for agent in agent_names:
            pids = get_process_pids(agent)
            current_pid = os.getpid()
            for pid in pids:
                if pid == current_pid:
                    continue
                try:
                    # Send SIGINT first to let the prompt interrupt gracefully, fallback to SIGTERM
                    os.kill(pid, signal.SIGINT)
                    halted_pids.append(pid)
                    logger.warning(f"Sent SIGINT to {agent} process PID {pid}")
                except OSError as err:
                    logger.debug(f"Could not signal PID {pid}: {err}")

        # 2. Clear all active agent signals
        for sig in ["antigravity", "claude", "codex", "manual", "custom"]:
            clear_signal(sig)

        # 3. Create persistent lockout flag
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(THERMAL_LOCKOUT_FILE, "w", encoding="utf-8") as f:
                f.write(f"{time.time()}:{reason}")
        except OSError:
            pass

        # 4. Notify user via macOS notification
        self.notify_user(
            title="AI Sleep Guard: Emergency Halt",
            message="Hardware temperature exceeded safety threshold! Prompts stopped to prevent overheating."
        )

        # 5. Telemetry record
        state_code, state_name = self.query_ns_thermal_state()
        report = {
            "reason": reason,
            "thermal_state": state_name,
            "thermal_code": state_code,
            "halted_pids": halted_pids,
            "timestamp": time.time()
        }
        record_event("THERMAL_EMERGENCY_HALT", report, status="ALERT")
        return report

    @staticmethod
    def clear_thermal_lockout() -> None:
        """Clears the thermal lockout file when temperatures return to normal."""
        try:
            if os.path.exists(THERMAL_LOCKOUT_FILE):
                os.remove(THERMAL_LOCKOUT_FILE)
                logger.info("Thermal lockout cleared; temperatures returned to safe levels.")
        except OSError:
            pass
