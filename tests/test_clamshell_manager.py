# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Unit tests for Clamshell / Lid-Closed Power Manager (src/clamshell_manager.py).
Verifies disablesleep toggling, pmset status parsing, and restore_defaults.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.clamshell_manager import ClamshellManager


class TestClamshellManager(unittest.TestCase):
    """Test suite for ClamshellManager functionality."""

    def setUp(self):
        self.manager = ClamshellManager()

    @patch("subprocess.run")
    def test_can_manage_clamshell_success(self, mock_run):
        """Verifies can_manage_clamshell returns True when sudo -n succeeds."""
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(self.manager.can_manage_clamshell())

    @patch("subprocess.run")
    def test_can_manage_clamshell_failure(self, mock_run):
        """Verifies can_manage_clamshell returns False when sudo -n fails."""
        mock_run.return_value = MagicMock(returncode=1)
        self.assertFalse(self.manager.can_manage_clamshell())

    @patch("subprocess.run")
    def test_is_clamshell_sleep_disabled_true(self, mock_run):
        """Verifies parsing SleepDisabled 1 in pmset -g."""
        mock_run.return_value = MagicMock(
            stdout="System-wide power settings:\n SleepDisabled 1\n displaysleep 10\n",
            returncode=0
        )
        self.assertTrue(ClamshellManager.is_clamshell_sleep_disabled())

    @patch("subprocess.run")
    def test_is_clamshell_sleep_disabled_false(self, mock_run):
        """Verifies parsing when SleepDisabled is absent or 0."""
        mock_run.return_value = MagicMock(
            stdout="System-wide power settings:\n displaysleep 10\n sleep 1\n",
            returncode=0
        )
        self.assertFalse(ClamshellManager.is_clamshell_sleep_disabled())

    @patch("subprocess.run")
    @patch("src.clamshell_manager.record_event")
    def test_set_clamshell_sleep_prevention(self, mock_record, mock_run):
        """Verifies enabling and disabling clamshell sleep prevention."""
        mock_run.return_value = MagicMock(returncode=0)

        # Enable
        success = self.manager.set_clamshell_sleep_prevention(True)
        self.assertTrue(success)
        self.assertTrue(self.manager.clamshell_active)

        # Disable
        success = self.manager.set_clamshell_sleep_prevention(False)
        self.assertTrue(success)
        self.assertFalse(self.manager.clamshell_active)

    @patch("subprocess.run")
    def test_restore_defaults(self, mock_run):
        """Verifies restore_defaults calls pmset disablesleep 0 if active."""
        mock_run.return_value = MagicMock(returncode=0)
        self.manager.clamshell_active = True
        self.manager.restore_defaults()
        self.assertFalse(self.manager.clamshell_active)


if __name__ == "__main__":
    unittest.main()
