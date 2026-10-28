# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Detectors package for AI agent prompt and execution activity.
"""

from .base import (
    ensure_signal_dir,
    get_signal_file_path,
    is_signal_active,
    set_signal_active,
    clear_signal,
    get_file_age_seconds,
    get_process_pids,
    has_child_processes
)
from .antigravity import check_antigravity_activity
from .claude import check_claude_activity
from .codex import check_codex_activity

__all__ = [
    "ensure_signal_dir",
    "get_signal_file_path",
    "is_signal_active",
    "set_signal_active",
    "clear_signal",
    "get_file_age_seconds",
    "get_process_pids",
    "has_child_processes",
    "check_antigravity_activity",
    "check_claude_activity",
    "check_codex_activity"
]
