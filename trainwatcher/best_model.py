"""Duck-typed best-model extraction helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional


def extract(candidate: Any) -> Optional[Dict[str, Any]]:
    """Extract a compact best-model summary from sklearn-like objects.

    Supported by duck typing only. No sklearn import is required.
    """
    if candidate is None:
        return None

    estimator = getattr(candidate, "best_estimator_", None)
    params = getattr(candidate, "best_params_", None)
    score = _coerce_float(getattr(candidate, "best_score_", None))
    index = getattr(candidate, "best_index_", None)

    if estimator is None and params is None and score is None:
        return None

    target = estimator if estimator is not None else candidate
    summary: Dict[str, Any] = {
        "model": _model_name(target),
        "score": score,
        "params": _sanitize_params(params),
        "index": index,
    }

    estimator_name = _model_name(estimator) if estimator is not None else None
    if estimator_name and estimator_name != summary["model"]:
        summary["estimator"] = estimator_name

    return summary


def _model_name(obj: Any) -> str:
    return obj.__class__.__name__


def _sanitize_params(params: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(params, dict):
        return None
    sanitized: Dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[str(key)] = value
        else:
            sanitized[str(key)] = repr(value)
    return sanitized


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
