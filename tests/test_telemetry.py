# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Unit tests for Cloud Firestore Telemetry and local audit logger.
"""

import json
import os
import unittest

from src.telemetry import record_event, get_local_log_path


class TestTelemetry(unittest.TestCase):
    """Verifies operational logging and event format."""

    def test_record_event_locally(self):
        """Verifies local audit JSONL persistence."""
        log_path = get_local_log_path()
        initial_lines = 0
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                initial_lines = len(f.readlines())

        payload = record_event(
            "TEST_EVENT",
            {"test_key": "test_value", "number": 42},
            status="INFO"
        )

        self.assertEqual(payload["appId"], "mac-anti-sleep")
        self.assertEqual(payload["eventType"], "TEST_EVENT")
        self.assertEqual(payload["status"], "INFO")
        self.assertIn("timestamp", payload)
        self.assertIn("unixTimestamp", payload)

        self.assertTrue(os.path.exists(log_path))
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertGreater(len(lines), initial_lines)
        last_entry = json.loads(lines[-1])
        self.assertEqual(last_entry["eventType"], "TEST_EVENT")
        self.assertEqual(last_entry["details"]["number"], 42)


if __name__ == "__main__":
    unittest.main()
