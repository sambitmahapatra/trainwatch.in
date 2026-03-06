"""Markdown report rendering for TrainWatcher runs."""

from __future__ import annotations

from typing import Any, Dict, List

from . import rules
from . import suggestions as suggestions_module


def generate(payload: Dict[str, Any]) -> str:
    """Render a Markdown report from a normalized runtime payload."""
    analysis = payload.get("analysis") or {}
    if not analysis or analysis.get("status") == "not_run":
        analysis = rules.analyze(payload)
    analysis = suggestions_module.attach_suggestions(analysis)

    lines: List[str] = [
        "# TrainWatcher Report",
        "",
        f"Status: {payload.get('status', 'unknown')}",
        f"Runtime: {payload.get('runtime', {}).get('human', 'unknown')}",
    ]

    error = payload.get("error", {})
    if error.get("message") or error.get("type"):
        lines.append(f"Error: {error.get('message') or error.get('type')}")

    progress = payload.get("progress", {})
    if progress.get("epochs") is not None:
        lines.append(f"Epochs: {progress['epochs']}")

    best = payload.get("metrics", {}).get("best", {})
    if best.get("val_accuracy"):
        val_acc = best["val_accuracy"]
        lines.append(f"Best Validation Accuracy: {val_acc['value']:.4g}")
        if val_acc.get("epoch") is not None:
            lines.append(f"Epoch of Best Model: {val_acc['epoch']}")

    best_model = payload.get("best_model")
    if isinstance(best_model, dict):
        lines.extend(["", "## Best Model"])
        if best_model.get("model"):
            lines.append(f"Model: {best_model['model']}")
        if best_model.get("score") is not None:
            lines.append(f"Score: {best_model['score']}")
        params = best_model.get("params")
        if isinstance(params, dict) and params:
            lines.append("Parameters:")
            for key, value in sorted(params.items()):
                lines.append(f"- {key}: {value}")

    last = payload.get("metrics", {}).get("last") or {}
    if last.get("train_loss") is not None:
        lines.append(f"Final Loss: {last['train_loss']}")
    if last.get("train_accuracy") is not None:
        lines.append(f"Final Accuracy: {last['train_accuracy']}")

    diagnosis_heading = "## Likely Cause" if payload.get("status") == "failed" else "## Observation"
    lines.extend(["", diagnosis_heading, analysis.get("reason") or "No analysis available."])

    suggestions = analysis.get("suggestions") or []
    if suggestions:
        lines.extend(["", "## Suggestions"])
        lines.extend([f"- {item}" for item in suggestions])

    interpretation = payload.get("interpretation") or {}
    if interpretation.get("text"):
        heading = "## LLM Diagnosis" if payload.get("status") == "failed" else "## LLM Interpretation"
        lines.extend(["", heading, str(interpretation["text"])])
    elif interpretation.get("error"):
        heading = "## LLM Diagnosis" if payload.get("status") == "failed" else "## LLM Interpretation"
        lines.extend(["", heading, f"Unavailable: {interpretation['error']}"])

    return "\n".join(lines)
