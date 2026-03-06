import unittest

from trainwatcher import metrics


class MetricsTests(unittest.TestCase):
    def test_normalize_history_maps_common_aliases(self) -> None:
        history = metrics.normalize_history(
            [
                {
                    "epoch": 1,
                    "loss": 0.8,
                    "val_acc": 0.72,
                    "lr": 0.001,
                }
            ]
        )

        self.assertEqual(history[0]["train_loss"], 0.8)
        self.assertEqual(history[0]["val_accuracy"], 0.72)
        self.assertEqual(history[0]["learning_rate"], 0.001)

    def test_runtime_payload_contains_best_metrics_and_progress(self) -> None:
        state = {"status": "completed", "runtime_seconds": 120}
        payload = metrics.build_runtime_payload(
            state,
            [
                {"epoch": 1, "loss": 0.8, "val_accuracy": 0.70},
                {"epoch": 2, "loss": 0.5, "val_accuracy": 0.81},
            ],
        )

        self.assertEqual(payload["runtime"]["seconds"], 120)
        self.assertEqual(payload["progress"]["epochs"], 2)
        self.assertEqual(payload["metrics"]["best"]["val_accuracy"]["value"], 0.81)
        self.assertEqual(payload["analysis"]["status"], "not_run")


if __name__ == "__main__":
    unittest.main()
