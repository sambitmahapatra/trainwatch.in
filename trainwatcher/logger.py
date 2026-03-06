"""Metric logging utilities."""

from typing import Any, Dict, List, Optional

_metrics: List[Dict[str, Any]] = []


def log(**metrics: Any) -> Dict[str, Any]:
    """Record a metrics snapshot for the current training run."""
    if not metrics:
        raise ValueError("No metrics provided to log().")
    entry = dict(metrics)
    _metrics.append(entry)
    return entry


def get_metrics() -> List[Dict[str, Any]]:
    """Return a copy of all logged metrics."""
    return [dict(m) for m in _metrics]


def last_metrics() -> Optional[Dict[str, Any]]:
    """Return the most recent metrics entry, if any."""
    if not _metrics:
        return None
    return dict(_metrics[-1])


def reset() -> None:
    """Clear all logged metrics."""
    _metrics.clear()
