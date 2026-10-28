# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Unit tests for AI agent prompt detectors.
"""

import os
import sqlite3
import tempfile
import time
import unittest

from src.detectors.base import (
    ensure_signal_dir,
    get_signal_file_path,
    is_signal_active,
    set_signal_active,
    clear_signal,
    get_file_age_seconds
)
from src.detectors.antigravity import check_antigravity_activity
from src.detectors.claude import check_claude_activity
from src.detectors.codex import check_codex_activity


class TestDetectors(unittest.TestCase):
    """Verifies agent activity detection logic."""

    def setUp(self):
        clear_signal("test_agent")
        clear_signal("claude")
        clear_signal("codex")
        clear_signal("antigravity")

    def tearDown(self):
        clear_signal("test_agent")
        clear_signal("claude")
        clear_signal("codex")
        clear_signal("antigravity")

    def test_signal_lifecycle(self):
        """Verifies creating, inspecting, and removing agent signal files."""
        active, age = is_signal_active("test_agent")
        self.assertFalse(active)
        self.assertIsNone(age)

        set_signal_active("test_agent")
        active, age = is_signal_active("test_agent", max_age_seconds=10.0)
        self.assertTrue(active)
        self.assertIsNotNone(age)
        self.assertLessEqual(age, 2.0)

        clear_signal("test_agent")
        active, age = is_signal_active("test_agent")
        self.assertFalse(active)

    def test_file_age_calculation(self):
        """Verifies file age helper with a temporary file."""
        with tempfile.NamedTemporaryFile() as tf:
            age = get_file_age_seconds(tf.name)
            self.assertIsNotNone(age)
            self.assertLessEqual(age, 2.0)

        # Non-existent file returns None
        self.assertIsNone(get_file_age_seconds("/tmp/non_existent_file_xyz_123"))

    def test_antigravity_detector_signal(self):
        """Verifies Antigravity detector responds immediately to active signal."""
        set_signal_active("antigravity")
        active, details = check_antigravity_activity()
        self.assertTrue(active)
        self.assertIn("explicit_signal_active", details["reason"])

    def test_claude_detector_signal(self):
        """Verifies Claude Code detector responds immediately to active signal."""
        set_signal_active("claude")
        active, details = check_claude_activity()
        self.assertTrue(active)
        self.assertIn("explicit_signal_active", details["reason"])

    def test_codex_detector_signal(self):
        """Verifies OpenAI Codex detector responds immediately to active signal."""
        set_signal_active("codex")
        active, details = check_codex_activity()
        self.assertTrue(active)
        self.assertIn("explicit_signal_active", details["reason"])


if __name__ == "__main__":
    unittest.main()
