import unittest

from trainwatch import summary


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
            "error_message": "CUDA Out Of Memory",
        }
        metrics = [{"epoch": 2, "loss": 0.4}]
        text = summary.generate(state, metrics)
        self.assertIn("Training Failed", text)
        self.assertIn("Error:", text)


if __name__ == "__main__":
    unittest.main()
