# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Unit tests for Thermal Safety Guard (src/thermal.py).
Verifies thermal state querying, pmset therm parsing, emergency halt execution,
and lockout lifecycle.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from src.thermal import (
    ThermalGuard,
    THERMAL_STATE_NOMINAL,
    THERMAL_STATE_FAIR,
    THERMAL_STATE_SERIOUS,
    THERMAL_STATE_CRITICAL,
    THERMAL_LOCKOUT_FILE
)


class TestThermalGuard(unittest.TestCase):
    """Test suite for ThermalGuard functionality."""

    def setUp(self):
        self.guard = ThermalGuard()
        self.guard.clear_thermal_lockout()

    def tearDown(self):
        self.guard.clear_thermal_lockout()

    def test_query_ns_thermal_state_live(self):
        """Verifies querying live Apple NSProcessInfo returns valid code and name."""
        code, name = self.guard.query_ns_thermal_state()
        self.assertIn(code, [
            THERMAL_STATE_NOMINAL,
            THERMAL_STATE_FAIR,
            THERMAL_STATE_SERIOUS,
            THERMAL_STATE_CRITICAL
        ])
        self.assertIsInstance(name, str)

    @patch("subprocess.run")
    def test_query_pmset_thermal_normal(self, mock_run):
        """Verifies parsing pmset -g therm with no warnings."""
        mock_run.return_value = MagicMock(
            stdout="Note: No thermal warning level has been recorded\nNote: No CPU power status has been recorded\n",
            returncode=0
        )
        res = ThermalGuard.query_pmset_thermal()
        self.assertIsNone(res["cpu_speed_limit"])
        self.assertFalse(res["has_thermal_warning"])

    @patch("subprocess.run")
    def test_query_pmset_thermal_throttled(self, mock_run):
        """Verifies parsing pmset -g therm when CPU is throttled to 50%."""
        mock_run.return_value = MagicMock(
            stdout="CPU_Speed_Limit = 50\nThermal Warning Level = 1\n",
            returncode=0
        )
        res = ThermalGuard.query_pmset_thermal()
        self.assertEqual(res["cpu_speed_limit"], 50)
        self.assertTrue(res["has_thermal_warning"])

    @patch.object(ThermalGuard, "query_ns_thermal_state")
    @patch.object(ThermalGuard, "query_pmset_thermal")
    def test_get_thermal_status_overheating(self, mock_pmset, mock_ns):
        """Verifies is_overheating is True when thermalState is Serious."""
        mock_ns.return_value = (THERMAL_STATE_SERIOUS, "Serious")
        mock_pmset.return_value = {"cpu_speed_limit": None, "has_thermal_warning": False, "raw_output": ""}

        status = self.guard.get_thermal_status()
        self.assertTrue(status["is_overheating"])
        self.assertEqual(status["thermal_state_code"], THERMAL_STATE_SERIOUS)
        self.assertEqual(status["thermal_state_name"], "Serious")

    @patch("os.kill")
    @patch("src.thermal.get_process_pids")
    @patch.object(ThermalGuard, "notify_user")
    @patch("src.thermal.record_event")
    def test_execute_emergency_halt(self, mock_record, mock_notify, mock_pids, mock_kill):
        """Verifies emergency halt creates lockout file, signals mock processes, and triggers notification."""
        mock_pids.return_value = [99999]
        report = self.guard.execute_emergency_halt(reason="test_emergency_halt")
        self.assertEqual(report["reason"], "test_emergency_halt")
        self.assertIn(99999, report["halted_pids"])
        self.assertTrue(os.path.exists(THERMAL_LOCKOUT_FILE))

        # Test clearing lockout
        self.guard.clear_thermal_lockout()
        self.assertFalse(os.path.exists(THERMAL_LOCKOUT_FILE))


if __name__ == "__main__":
    unittest.main()
