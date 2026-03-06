import unittest

from trainwatcher import best_model
from trainwatcher import monitor


class DummyEstimator:
    pass


class DummySearch:
    best_params_ = {"max_depth": 12, "n_estimators": 200}
    best_score_ = 0.89
    best_estimator_ = DummyEstimator()
    best_index_ = 3


class BestModelTests(unittest.TestCase):
    def test_extracts_sklearn_like_summary(self) -> None:
        result = best_model.extract(DummySearch())
        self.assertIsNotNone(result)
        self.assertEqual(result["model"], "DummyEstimator")
        self.assertEqual(result["score"], 0.89)
        self.assertEqual(result["params"]["max_depth"], 12)

    def test_monitor_summary_includes_best_model(self) -> None:
        monitor.reset()
        monitor.start()
        monitor.set_best_model(DummySearch())
        snapshot = monitor.end(config={"notifications": {}, "logging": {"enabled": False}})
        self.assertIn("Best Model:", snapshot["summary"])


if __name__ == "__main__":
    unittest.main()
