import unittest

from trainwatcher import metrics
from trainwatcher import report


class ReportTests(unittest.TestCase):
    def test_report_renders_observation_and_suggestions(self) -> None:
        payload = metrics.build_runtime_payload(
            {"status": "completed", "runtime_seconds": 75},
            [
                {"epoch": 1, "loss": 0.9, "val_loss": 0.8},
                {"epoch": 2, "loss": 0.7, "val_loss": 0.85},
                {"epoch": 3, "loss": 0.5, "val_loss": 0.92},
                {"epoch": 4, "loss": 0.3, "val_loss": 1.05},
            ],
        )

        text = report.generate(payload)
        self.assertIn("# TrainWatcher Report", text)
        self.assertIn("## Observation", text)
        self.assertIn("## Suggestions", text)


if __name__ == "__main__":
    unittest.main()
