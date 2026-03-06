import unittest

from trainwatcher import summary


class SummaryTests(unittest.TestCase):
    def test_summary_completed(self) -> None:
        state = {"status": "completed", "runtime_seconds": 65}
        metrics = [{"epoch": 1, "loss": 0.5, "val_acc": 0.8}]
        text = summary.generate(state, metrics)
        self.assertIn("Training Completed", text)
        self.assertIn("Runtime:", text)

    def test_summary_failed(self) -> None:
        state = {
            "status": "failed",
            "runtime_seconds": 10,
            "error_message": "Target 5 is out of bounds.",
        }
        metrics = [{"epoch": 2, "loss": 0.4}]
        text = summary.generate(state, metrics)
        self.assertIn("Training Failed", text)
        self.assertIn("Error:", text)
        self.assertIn("Likely Cause:", text)
        self.assertIn("Suggestions:", text)

    def test_summary_includes_phase_two_observation(self) -> None:
        state = {"status": "completed", "runtime_seconds": 120}
        metrics = [
            {"epoch": 1, "loss": 0.9, "val_loss": 0.8},
            {"epoch": 2, "loss": 0.7, "val_loss": 0.85},
            {"epoch": 3, "loss": 0.5, "val_loss": 0.92},
            {"epoch": 4, "loss": 0.3, "val_loss": 1.05},
        ]
        text = summary.generate(state, metrics)
        self.assertIn("Observation:", text)
        self.assertIn("Suggestions:", text)


if __name__ == "__main__":
    unittest.main()
