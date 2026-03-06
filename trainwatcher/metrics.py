"""Normalized metric extraction and runtime payload helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .contracts import make_analysis_result
from .utils.time_utils import format_duration

METRIC_ALIASES: Dict[str, Tuple[str, ...]] = {
    "epoch": ("epoch", "epochs", "current_epoch"),
    "step": ("step", "steps", "global_step"),
    "train_loss": ("train_loss", "loss", "training_loss"),
    "val_loss": ("val_loss", "validation_loss", "valid_loss", "eval_loss"),
    "train_accuracy": ("train_accuracy", "accuracy", "acc", "train_acc"),
    "val_accuracy": (
        "val_accuracy",
        "val_acc",
        "validation_accuracy",
        "valid_accuracy",
        "eval_accuracy",
        "eval_acc",
    ),
    "learning_rate": ("learning_rate", "lr"),
}

SERIES_KEYS: Tuple[str, ...] = (
    "train_loss",
    "val_loss",
    "train_accuracy",
    "val_accuracy",
    "learning_rate",
)

BEST_METRIC_MODES: Dict[str, str] = {
    "train_loss": "min",
    "val_loss": "min",
    "train_accuracy": "max",
    "val_accuracy": "max",
}


def normalize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one metric entry to canonical keys while preserving extras."""
    normalized = dict(entry)
    for canonical, aliases in METRIC_ALIASES.items():
        if canonical in normalized:
            continue
        for alias in aliases:
            if alias in entry:
                normalized[canonical] = entry[alias]
                break
    return normalized


def normalize_history(metrics: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize all metric entries."""
    return [normalize_entry(entry) for entry in metrics]


def build_runtime_payload(state: Dict[str, Any], metrics: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the normalized internal payload used for summaries and analysis."""
    history = normalize_history(metrics)
    last_entry = history[-1] if history else None
    available_keys = sorted({key for entry in history for key in entry.keys()})

    series: Dict[str, List[Dict[str, Any]]] = {}
    for key in SERIES_KEYS:
        points = _build_series(history, key)
        if points:
            series[key] = points

    best: Dict[str, Dict[str, Any]] = {}
    for key, mode in BEST_METRIC_MODES.items():
        candidate = _best_metric(series.get(key, []), mode=mode)
        if candidate is not None:
            best[key] = candidate

    return {
        "status": state.get("status", "unknown"),
        "start_time": _isoformat(state.get("start_time")),
        "end_time": _isoformat(state.get("end_time")),
        "runtime": {
            "seconds": state.get("runtime_seconds"),
            "human": format_duration(state.get("runtime_seconds")),
        },
        "error": {
            "type": state.get("error_type"),
            "message": state.get("error_message"),
        },
        "best_model": state.get("best_model"),
        "progress": {
            "entries": len(history),
            "epochs": _last_value(history, "epoch"),
            "last_step": _last_value(history, "step"),
        },
        "metrics": {
            "history": history,
            "last": last_entry,
            "available": available_keys,
            "series": series,
            "best": best,
        },
        "analysis": make_analysis_result(
            status="not_run",
            confidence=0.0,
            reason="Analysis not computed.",
            source="rule",
        ),
    }


def _build_series(history: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for index, entry in enumerate(history):
        value = _to_numeric(entry.get(key))
        if value is None:
            continue
        points.append(
            {
                "index": index,
                "epoch": entry.get("epoch"),
                "step": entry.get("step"),
                "value": value,
            }
        )
    return points


def _best_metric(points: List[Dict[str, Any]], mode: str) -> Optional[Dict[str, Any]]:
    if not points:
        return None
    best = points[0]
    for point in points[1:]:
        if mode == "min" and point["value"] < best["value"]:
            best = point
        elif mode == "max" and point["value"] > best["value"]:
            best = point
    return dict(best)


def _last_value(history: List[Dict[str, Any]], key: str) -> Optional[Any]:
    for entry in reversed(history):
        value = entry.get(key)
        if value is not None:
            return value
    return None


def _to_numeric(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _isoformat(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return value if isinstance(value, str) else None
