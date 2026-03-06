import json
import unittest
from unittest import mock

from trainwatcher import cloud
from trainwatcher import llm
from trainwatcher import summary


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class LLMTests(unittest.TestCase):
    def test_hosted_interpretation_uses_backend_response(self) -> None:
        payload = {"status": "completed"}
        analysis = {"reason": "Validation loss increased."}

        with mock.patch(
            "trainwatcher.cloud.load_credentials",
            return_value={"api_key": "cloud-key", "base_url": "https://example.workers.dev"},
        ), mock.patch(
            "trainwatcher.cloud._post_json",
            return_value={"text": "Hosted explanation", "provider": "hosted", "model": "llama-3.1-8b-instant"},
        ):
            result = cloud.request_interpretation(payload, analysis, mode="hybrid")

        self.assertEqual(result["provider"], "hosted")
        self.assertEqual(result["text"], "Hosted explanation")

    def test_openai_compatible_interpretation_success(self) -> None:
        payload = {
            "status": "completed",
            "runtime": {"human": "2m"},
            "progress": {"epochs": 4},
            "metrics": {"best": {}, "last": {}},
            "best_model": None,
        }
        analysis = {"reason": "Validation loss increased.", "suggestions": ["Enable early stopping."]}

        with mock.patch(
            "trainwatcher.llm.urllib.request.urlopen",
            return_value=_FakeResponse(
                {
                    "choices": [
                        {"message": {"content": "The run appears mildly overfit. Use early stopping."}}
                    ]
                }
            ),
        ):
            result = llm.interpret(
                payload,
                analysis,
                {
                    "api_key": "test-key",
                    "base_url": "https://api.groq.com/openai/v1",
                    "model": "llama-3.1-8b-instant",
                },
            )

        self.assertEqual(result["provider"], "groq")
        self.assertIn("overfit", result["text"])

    def test_summary_falls_back_to_rule_when_hosted_llm_errors(self) -> None:
        state = {"status": "completed", "runtime_seconds": 90}
        metrics = [
            {"epoch": 1, "loss": 0.9, "val_loss": 0.8},
            {"epoch": 2, "loss": 0.7, "val_loss": 0.85},
            {"epoch": 3, "loss": 0.5, "val_loss": 0.92},
            {"epoch": 4, "loss": 0.3, "val_loss": 1.05},
        ]
        config = {
            "interpretation": {
                "mode": "llm",
            }
        }

        with mock.patch("trainwatcher.summary.cloud_module.request_interpretation", side_effect=RuntimeError("quota")):
            text = summary.generate(state, metrics, config=config)

        self.assertIn("Observation:", text)
        self.assertNotIn("LLM Interpretation:", text)

    def test_summary_uses_byok_fallback_if_enabled(self) -> None:
        state = {"status": "completed", "runtime_seconds": 90}
        metrics = [
            {"epoch": 1, "loss": 0.9, "val_loss": 0.8},
            {"epoch": 2, "loss": 0.7, "val_loss": 0.85},
            {"epoch": 3, "loss": 0.5, "val_loss": 0.92},
            {"epoch": 4, "loss": 0.3, "val_loss": 1.05},
        ]
        config = {
            "interpretation": {
                "mode": "hybrid",
                "fallback": "byok",
                "byok": {
                    "api_key": "test-key",
                    "base_url": "https://api.groq.com/openai/v1",
                    "model": "llama-3.1-8b-instant",
                },
            }
        }

        with mock.patch("trainwatcher.summary.cloud_module.request_interpretation", side_effect=RuntimeError("quota")), mock.patch(
            "trainwatcher.summary.llm_module.interpret",
            return_value={"mode": "hybrid", "text": "BYOK explanation", "provider": "groq", "model": "llama-3.1-8b-instant", "error": None},
        ):
            text = summary.generate(state, metrics, config=config)

        self.assertIn("Observation:", text)
        self.assertIn("LLM Interpretation:", text)

    def test_failed_summary_uses_hosted_diagnosis_when_enabled(self) -> None:
        state = {
            "status": "failed",
            "runtime_seconds": 3,
            "error_type": "RuntimeError",
            "error_message": "Target 5 is out of bounds.",
        }
        config = {
            "interpretation": {
                "mode": "hybrid",
            }
        }

        with mock.patch(
            "trainwatcher.summary.cloud_module.request_interpretation",
            return_value={
                "mode": "hybrid",
                "text": "The output layer has fewer classes than the dataset labels.",
                "provider": "hosted",
                "model": "llama-3.1-8b-instant",
                "error": None,
            },
        ):
            text = summary.generate(state, [], config=config)

        self.assertIn("Likely Cause:", text)
        self.assertIn("LLM Diagnosis:", text)


if __name__ == "__main__":
    unittest.main()
