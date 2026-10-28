# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Antigravity (Gemini) Active Prompt Detector.
Monitors SQLite conversation summaries, active transcripts, and signal files.
"""

import os
import sqlite3
import time
from typing import Tuple, Dict, Any, Optional

from .base import is_signal_active, get_file_age_seconds


ANTIGRAVITY_DIR = os.path.expanduser("~/.gemini/antigravity")
DB_PATH = os.path.join(ANTIGRAVITY_DIR, "conversation_summaries.db")
BRAIN_DIR = os.path.join(ANTIGRAVITY_DIR, "brain")


def check_antigravity_activity(
    max_db_age_seconds: float = 120.0,
    max_brain_age_seconds: float = 45.0
) -> Tuple[bool, Dict[str, Any]]:
    """
    Checks if Antigravity is actively executing a prompt, tool, or subagent.

    :param max_db_age_seconds: Maximum age for active conversation records in SQLite.
    :param max_brain_age_seconds: Maximum age for recently updated brain transcripts.
    :return: (is_active, details_dict)
    """
    details: Dict[str, Any] = {
        "agent": "antigravity",
        "active": False,
        "reason": "idle",
        "active_conversations": []
    }

    # 1. Signal file check
    sig_active, sig_age = is_signal_active("antigravity", max_age_seconds=max_brain_age_seconds)
    if sig_active:
        details["active"] = True
        details["reason"] = f"explicit_signal_active ({sig_age:.1f}s ago)"
        return True, details

    # 2. SQLite Database check
    if os.path.exists(DB_PATH):
        try:
            # Open SQLite in read-only immutable mode to avoid locks
            conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=1.0)
            cursor = conn.cursor()
            query = """
                SELECT conversation_id, status, not_fully_idle, datetime(last_modified_time),
                       (strftime('%s', 'now') - strftime('%s', last_modified_time)) as age_sec
                FROM conversation_summaries
                WHERE (status = 'CASCADE_RUN_STATUS_RUNNING' OR not_fully_idle = 1)
                  AND (strftime('%s', 'now') - strftime('%s', last_modified_time)) < ?
                ORDER BY last_modified_time DESC
                LIMIT 5
            """
            cursor.execute(query, (max_db_age_seconds,))
            rows = cursor.fetchall()
            conn.close()

            if rows:
                active_list = []
                for cid, status, not_idle, mtime_str, age_sec in rows:
                    active_list.append({
                        "id": cid,
                        "status": status,
                        "not_fully_idle": bool(not_idle),
                        "modified": mtime_str,
                        "age_seconds": age_sec
                    })
                details["active"] = True
                details["reason"] = f"sqlite_running_turns ({len(rows)} active)"
                details["active_conversations"] = active_list
                return True, details
        except Exception as db_err:
            details["db_error"] = str(db_err)

    # 3. Brain transcript file mtime check
    if os.path.isdir(BRAIN_DIR):
        try:
            now = time.time()
            for entry in os.scandir(BRAIN_DIR):
                if entry.is_dir():
                    transcript_path = os.path.join(
                        entry.path, ".system_generated", "logs", "transcript.jsonl"
                    )
                    age = get_file_age_seconds(transcript_path)
                    if age is not None and age <= max_brain_age_seconds:
                        details["active"] = True
                        details["reason"] = f"transcript_writing ({age:.1f}s ago in {entry.name[:8]}...)"
                        details["active_conversations"].append({
                            "id": entry.name,
                            "transcript_age": age
                        })
                        return True, details
        except Exception as scan_err:
            details["scan_error"] = str(scan_err)

    return False, details
