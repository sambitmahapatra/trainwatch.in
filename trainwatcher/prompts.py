"""Prompt builders for optional OpenAI-compatible interpretation."""

from __future__ import annotations

from typing import Any, Dict, List


SYSTEM_PROMPT = (
    "You explain machine learning training behavior from aggregated metrics only. "
    "Keep the answer concise, practical, and under 120 words. "
    "Do not ask follow-up questions."
)


def build_messages(payload: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build OpenAI-compatible chat messages for training interpretation."""
    status = payload.get("status", "unknown")
    metrics = payload.get("metrics", {})
    best = metrics.get("best", {})
    last = metrics.get("last") or {}
    progress = payload.get("progress", {})

    lines = [
        "Training Summary",
        f"Status: {status}",
        f"Runtime: {payload.get('runtime', {}).get('human', 'unknown')}",
    ]
    if progress.get("epochs") is not None:
        lines.append(f"Epochs: {progress['epochs']}")

    if best.get("val_accuracy"):
        item = best["val_accuracy"]
        lines.append(f"Best validation accuracy: {item['value']:.4g}")
        if item.get("epoch") is not None:
            lines.append(f"Epoch of best validation accuracy: {item['epoch']}")

    if best.get("val_loss"):
        item = best["val_loss"]
        lines.append(f"Best validation loss: {item['value']:.4g}")

    if last.get("train_loss") is not None:
        lines.append(f"Final training loss: {last['train_loss']}")
    if last.get("val_loss") is not None:
        lines.append(f"Final validation loss: {last['val_loss']}")
    if last.get("train_accuracy") is not None:
        lines.append(f"Final training accuracy: {last['train_accuracy']}")
    if last.get("val_accuracy") is not None:
        lines.append(f"Final validation accuracy: {last['val_accuracy']}")

    error = payload.get("error") or {}
    if error.get("type"):
        lines.append(f"Error type: {error['type']}")
    if error.get("message"):
        lines.append(f"Error message: {error['message']}")

    if payload.get("best_model"):
        model = payload["best_model"]
        if model.get("model"):
            lines.append(f"Best model: {model['model']}")
        if model.get("score") is not None:
            lines.append(f"Best model score: {model['score']}")

    lines.append(f"Rule observation: {analysis.get('reason') or 'No strong rule signal.'}")
    if analysis.get("suggestions"):
        lines.append("Rule suggestions: " + "; ".join(analysis["suggestions"][:3]))

    lines.append("")
    if status == "failed":
        lines.append("Diagnose the failure and suggest practical fixes.")
    else:
        lines.append("Explain the training behavior and suggest practical next steps.")

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]
