import unittest

from trainwatcher import metrics
from trainwatcher import rules


def _payload(history):
    return metrics.build_runtime_payload({"status": "completed", "runtime_seconds": 30}, history)


def _failed_payload(error_message, error_type="RuntimeError", history=None):
    return metrics.build_runtime_payload(
        {
            "status": "failed",
            "runtime_seconds": 5,
            "error_type": error_type,
            "error_message": error_message,
        },
        history or [],
    )


class RuleEngineTests(unittest.TestCase):
    def test_detects_overfitting(self) -> None:
        payload = _payload(
            [
                {"epoch": 1, "loss": 0.9, "val_loss": 0.8},
                {"epoch": 2, "loss": 0.7, "val_loss": 0.85},
                {"epoch": 3, "loss": 0.5, "val_loss": 0.92},
                {"epoch": 4, "loss": 0.3, "val_loss": 1.05},
            ]
        )

        result = rules.analyze(payload)
        self.assertEqual(result["status"], "overfitting")

    def test_detects_plateau(self) -> None:
        payload = _payload(
            [
                {"epoch": 1, "val_accuracy": 0.80},
                {"epoch": 2, "val_accuracy": 0.801},
                {"epoch": 3, "val_accuracy": 0.8015},
                {"epoch": 4, "val_accuracy": 0.8017},
            ]
        )

        result = rules.analyze(payload, plateau_delta=0.005, plateau_patience=3)
        self.assertEqual(result["status"], "plateau")

    def test_detects_diverging_training(self) -> None:
        payload = _payload(
            [
                {"epoch": 1, "loss": 0.3},
                {"epoch": 2, "loss": 0.5},
                {"epoch": 3, "loss": 0.8},
                {"epoch": 4, "loss": 1.2},
            ]
        )

        result = rules.analyze(payload, divergence_patience=3)
        self.assertEqual(result["status"], "diverging")

    def test_detects_normal_convergence(self) -> None:
        payload = _payload(
            [
                {"epoch": 1, "loss": 1.0, "val_loss": 1.1},
                {"epoch": 2, "loss": 0.8, "val_loss": 0.95},
                {"epoch": 3, "loss": 0.6, "val_loss": 0.8},
                {"epoch": 4, "loss": 0.45, "val_loss": 0.7},
            ]
        )

        result = rules.analyze(payload)
        self.assertEqual(result["status"], "normal_convergence")

    def test_detects_failure_class_index_mismatch(self) -> None:
        payload = _failed_payload("Target 5 is out of bounds.")

        result = rules.analyze(payload)

        self.assertEqual(result["status"], "class_index_mismatch")
        self.assertIn("final layer class count", result["reason"])


if __name__ == "__main__":
    unittest.main()
