import unittest

from trainwatch import monitor


class MonitorTests(unittest.TestCase):
    def test_monitor_end_generates_summary(self) -> None:
        monitor.reset()
        monitor.start()
        monitor.log(epoch=1, loss=0.5, val_acc=0.8)
        snapshot = monitor.end(config={"notifications": {}, "logging": {"enabled": False}})

        self.assertEqual(snapshot["status"], "completed")
        self.assertIsNotNone(snapshot.get("summary"))


if __name__ == "__main__":
    unittest.main()
