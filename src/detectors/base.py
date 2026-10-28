# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Base abstractions and utilities for AI agent activity detectors.
Zero third-party dependencies: strictly uses Python standard library.
"""

import os
import subprocess
import time
from typing import Optional, Tuple, List


SIGNAL_DIR = "/tmp/ai_sleep_guard"


def ensure_signal_dir() -> str:
    """Ensures the temporary signal directory exists and returns its path."""
    os.makedirs(SIGNAL_DIR, exist_ok=True)
    return SIGNAL_DIR


def get_signal_file_path(agent_name: str) -> str:
    """Returns the signal file path for a given agent."""
    return os.path.join(ensure_signal_dir(), f"{agent_name}.active")


def is_signal_active(agent_name: str, max_age_seconds: float = 300.0) -> Tuple[bool, Optional[float]]:
    """
    Checks if a signal file exists and has been touched within max_age_seconds.

    :param agent_name: Name of the agent (antigravity, claude, codex).
    :param max_age_seconds: Maximum allowed age in seconds before considering stale.
    :return: (is_active, age_in_seconds)
    """
    sig_path = get_signal_file_path(agent_name)
    if not os.path.exists(sig_path):
        return False, None
    try:
        mtime = os.path.getmtime(sig_path)
        age = time.time() - mtime
        if age <= max_age_seconds:
            return True, age
        return False, age
    except OSError:
        return False, None


def set_signal_active(agent_name: str) -> None:
    """Marks an agent active by touching its signal file."""
    sig_path = get_signal_file_path(agent_name)
    ensure_signal_dir()
    try:
        with open(sig_path, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
    except OSError:
        pass


def clear_signal(agent_name: str) -> None:
    """Removes the agent signal file."""
    sig_path = get_signal_file_path(agent_name)
    try:
        if os.path.exists(sig_path):
            os.remove(sig_path)
    except OSError:
        pass


def get_file_age_seconds(file_path: str) -> Optional[float]:
    """Returns the age of a file in seconds, or None if the file does not exist."""
    try:
        if os.path.exists(file_path):
            return time.time() - os.path.getmtime(file_path)
    except OSError:
        pass
    return None


def get_process_pids(process_name_pattern: str) -> List[int]:
    """
    Finds running process IDs matching a pattern using pgrep.
    
    :param process_name_pattern: Exact name or regex pattern for pgrep.
    :return: List of process IDs (integers).
    """
    try:
        res = subprocess.run(
            ["pgrep", "-f", process_name_pattern],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res.returncode == 0:
            pids = []
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))
            return pids
    except Exception:
        pass
    return []


def has_child_processes(parent_pids: List[int]) -> bool:
    """
    Checks if any of the given parent processes currently have active child processes.
    """
    if not parent_pids:
        return False
    pid_strs = [str(p) for p in parent_pids]
    try:
        res = subprocess.run(
            ["pgrep", "-P", ",".join(pid_strs)],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        return res.returncode == 0 and len(res.stdout.strip()) > 0
    except Exception:
        return False
