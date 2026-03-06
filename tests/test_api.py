import unittest

from trainwatcher import monitor
from trainwatcher import watch


class PublicAPITests(unittest.TestCase):
    def test_watch_wrapper_runs_training_and_finishes(self) -> None:
        monitor.reset()

        def train():
            monitor.log(epoch=1, loss=0.4, val_accuracy=0.8)
            return "done"

        result = watch(train, interpretation="rule", config={"notifications": {}, "logging": {"enabled": False}})
        snapshot = monitor.snapshot()

        self.assertEqual(result, "done")
        self.assertEqual(snapshot["status"], "completed")
        self.assertIn("Training Completed", snapshot["summary"])


if __name__ == "__main__":
    unittest.main()
