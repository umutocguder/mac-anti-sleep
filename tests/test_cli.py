# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Unit tests for CLI commands and argument parsing.
"""

import io
import unittest
from unittest.mock import patch

from src.cli import main
from src.detectors.base import clear_signal, is_signal_active


class TestCLI(unittest.TestCase):
    """Verifies CLI arguments and command dispatch."""

    def setUp(self):
        clear_signal("claude")
        clear_signal("manual")

    def tearDown(self):
        clear_signal("claude")
        clear_signal("manual")

    def test_cli_ping_and_done(self):
        """Verifies ping and done commands via CLI."""
        with patch("sys.argv", ["ai-sleep-guard", "ping", "claude"]):
            main()
        active, _ = is_signal_active("claude")
        self.assertTrue(active)

        with patch("sys.argv", ["ai-sleep-guard", "done", "claude"]):
            main()
        active, _ = is_signal_active("claude")
        self.assertFalse(active)

    def test_cli_on_and_off(self):
        """Verifies manual override on and off commands."""
        with patch("sys.argv", ["ai-sleep-guard", "on"]):
            main()
        active, _ = is_signal_active("manual")
        self.assertTrue(active)

        with patch("sys.argv", ["ai-sleep-guard", "off"]):
            main()
        active, _ = is_signal_active("manual")
        self.assertFalse(active)

    def test_cli_status_output(self):
        """Verifies status command runs without exceptions and displays health checks."""
        with patch("sys.argv", ["ai-sleep-guard", "status"]), patch("sys.stdout", new=io.StringIO()) as fake_out:
            main()
            output = fake_out.getvalue()
            self.assertIn("AI Sleep Guard", output)
            self.assertIn("Antigravity", output)
            self.assertIn("Claude Code", output)
            self.assertIn("OpenAI Codex", output)
            self.assertIn("Thermal Protection", output)
            self.assertIn("Lid-Close Sleep Guard", output)

    def test_cli_thermal_output(self):
        """Verifies thermal diagnostics command outputs required sections."""
        with patch("sys.argv", ["ai-sleep-guard", "thermal"]), patch("sys.stdout", new=io.StringIO()) as fake_out:
            main()
            output = fake_out.getvalue()
            self.assertIn("Thermal Diagnostics", output)
            self.assertIn("macOS Thermal State", output)
            self.assertIn("Overheating Status", output)

    def test_cli_setup_sudo_output(self):
        """Verifies setup-sudo command outputs instructions or success message."""
        with patch("sys.argv", ["ai-sleep-guard", "setup-sudo"]), patch("sys.stdout", new=io.StringIO()) as fake_out:
            main()
            output = fake_out.getvalue()
            self.assertIn("Sudoers Configuration", output)


if __name__ == "__main__":
    unittest.main()
