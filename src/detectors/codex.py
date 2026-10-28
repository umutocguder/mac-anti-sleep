# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
OpenAI Codex Active Prompt Detector.
Monitors signal flags, active Codex CLI / App-server processes, child tools, and SQLite WAL updates.
"""

import os
from typing import Tuple, Dict, Any

from src.detectors.base import (
    is_signal_active,
    get_file_age_seconds,
    get_process_pids,
    has_child_processes
)


CODEX_DIR = os.path.expanduser("~/.codex")
LOGS_WAL = os.path.join(CODEX_DIR, "logs_2.sqlite-wal")
STATE_WAL = os.path.join(CODEX_DIR, "state_5.sqlite-wal")


def check_codex_activity(
    max_signal_age_seconds: float = 300.0,
    max_wal_age_seconds: float = 30.0
) -> Tuple[bool, Dict[str, Any]]:
    """
    Checks if Codex is actively executing a prompt or tool.

    :param max_signal_age_seconds: Maximum age of explicit hook/wrap signal.
    :param max_wal_age_seconds: Maximum age of recently touched SQLite WAL files.
    :return: (is_active, details_dict)
    """
    details: Dict[str, Any] = {
        "agent": "codex",
        "active": False,
        "reason": "idle",
        "pids": []
    }

    # 1. Signal file check
    sig_active, sig_age = is_signal_active("codex", max_age_seconds=max_signal_age_seconds)
    if sig_active:
        details["active"] = True
        details["reason"] = f"explicit_signal_active ({sig_age:.1f}s ago)"
        return True, details

    # 2. Check running processes
    codex_pids = get_process_pids("codex")
    current_pid = os.getpid()
    active_codex_pids = [p for p in codex_pids if p != current_pid]

    if not active_codex_pids:
        details["reason"] = "process_not_running"
        return False, details

    details["pids"] = active_codex_pids

    # 3. Check if Codex has active child processes (e.g. running shell commands, python, compiler)
    if has_child_processes(active_codex_pids):
        details["active"] = True
        details["reason"] = f"child_commands_active (parent pids: {active_codex_pids})"
        return True, details

    # 4. Check recent SQLite WAL write activity in ~/.codex
    for wal_path in [LOGS_WAL, STATE_WAL]:
        age = get_file_age_seconds(wal_path)
        if age is not None and age <= max_wal_age_seconds:
            details["active"] = True
            details["reason"] = f"recent_wal_activity_{os.path.basename(wal_path)} ({age:.1f}s ago)"
            return True, details

    return False, details
