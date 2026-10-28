# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Claude Code Active Prompt Detector.
Monitors signal flags, active Claude CLI processes, child command executions, and session activity.
"""

import os
import time
from typing import Tuple, Dict, Any

from src.detectors.base import (
    is_signal_active,
    get_file_age_seconds,
    get_process_pids,
    has_child_processes
)


CLAUDE_DIR = os.path.expanduser("~/.claude")
DEBUG_FILE = os.path.join(CLAUDE_DIR, "debug", "latest")
HISTORY_FILE = os.path.join(CLAUDE_DIR, "history.jsonl")


def check_claude_activity(
    max_signal_age_seconds: float = 300.0,
    max_file_age_seconds: float = 25.0
) -> Tuple[bool, Dict[str, Any]]:
    """
    Checks if Claude Code is actively executing a prompt or tool.

    :param max_signal_age_seconds: Maximum age of explicit hook signal.
    :param max_file_age_seconds: Maximum age of recently touched debug/session files.
    :return: (is_active, details_dict)
    """
    details: Dict[str, Any] = {
        "agent": "claude",
        "active": False,
        "reason": "idle",
        "pids": []
    }

    # 1. Signal file check (hook driven)
    sig_active, sig_age = is_signal_active("claude", max_age_seconds=max_signal_age_seconds)
    if sig_active:
        details["active"] = True
        details["reason"] = f"explicit_signal_active ({sig_age:.1f}s ago)"
        return True, details

    # 2. Check running processes
    # Find Claude CLI or node claude instances
    claude_pids = get_process_pids("claude")
    # Filter out our own scripts or grep
    current_pid = os.getpid()
    active_claude_pids = [p for p in claude_pids if p != current_pid]

    if not active_claude_pids:
        details["reason"] = "process_not_running"
        return False, details

    details["pids"] = active_claude_pids

    # 3. Check if Claude has active child processes (e.g. running bash commands, git, tests, build)
    if has_child_processes(active_claude_pids):
        details["active"] = True
        details["reason"] = f"child_commands_active (parent pids: {active_claude_pids})"
        return True, details

    # 4. Check recent file modifications in ~/.claude
    for target_path in [DEBUG_FILE, HISTORY_FILE]:
        age = get_file_age_seconds(target_path)
        if age is not None and age <= max_file_age_seconds:
            details["active"] = True
            details["reason"] = f"recent_activity_in_{os.path.basename(target_path)} ({age:.1f}s ago)"
            return True, details

    return False, details
