import os
import sys
import unittest

# Ensure the aws directory is on sys.path so tests can import lambda_function.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lambda_function import PowerScaleMonitor

class TestHealthScore(unittest.TestCase):
    def setUp(self):
        # Create an instance without running __init__ which requires env vars
        self.monitor = object.__new__(PowerScaleMonitor)

    def test_no_events_perfect_score(self):
        score, _ = self.monitor.calculate_health_score({})
        self.assertEqual(score, 100)

    def test_critical_event_deducts_20(self):
        score, _ = self.monitor.calculate_health_score({"eventgroups": [{"severity": "critical"}]})
        self.assertEqual(score, 80)

    def test_score_floors_at_zero(self):
        events = {"eventgroups": [{"severity": "critical"}] * 10}
        score, _ = self.monitor.calculate_health_score(events)
        self.assertEqual(score, 0)

if __name__ == "__main__":
    unittest.main()
