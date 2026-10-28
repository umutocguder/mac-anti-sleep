# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Unit tests for CaffeinateManager.
"""

import time
import unittest

from src.caffeinate_manager import CaffeinateManager


class TestCaffeinateManager(unittest.TestCase):
    """Verifies sleep assertion lifecycle and cooldown buffer."""

    def setUp(self):
        self.mgr = CaffeinateManager(default_cooldown_seconds=1.5)

    def tearDown(self):
        self.mgr.stop()

    def test_start_and_stop_caffeinate(self):
        """Verifies spawning and cleanly stopping the caffeinate process."""
        started = self.mgr.start(reason="unit_test")
        self.assertTrue(started)
        self.assertTrue(self.mgr.is_running())

        status = self.mgr.get_status()
        self.assertTrue(status["caffeinate_running"])
        self.assertIsNotNone(status["pid"])

        stopped = self.mgr.stop()
        self.assertTrue(stopped)
        self.assertFalse(self.mgr.is_running())

    def test_cooldown_logic(self):
        """Verifies cooldown window before allowing system sleep."""
        self.mgr.touch(reason="unit_test_cooldown")
        self.assertTrue(self.mgr.should_stay_awake(is_active_now=True))
        self.assertTrue(self.mgr.should_stay_awake(is_active_now=False, cooldown_seconds=2.0))

        remaining = self.mgr.get_cooldown_remaining(cooldown_seconds=2.0)
        self.assertGreater(remaining, 0.0)

        # After cooldown duration expires
        time.sleep(1.6)
        self.assertFalse(self.mgr.should_stay_awake(is_active_now=False, cooldown_seconds=1.5))


if __name__ == "__main__":
    unittest.main()
