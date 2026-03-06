"""Stable internal payload contracts for Phase-02 analysis."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


def make_analysis_result(
    status: str = "not_run",
    confidence: float = 0.0,
    reason: str = "",
    source: str = "rule",
    suggestions: Optional[Iterable[str]] = None,
    signals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a normalized analysis result payload.

    This stays intentionally small and dict-based so later rule/LLM modules
    can share one deterministic contract without adding runtime dependencies.
    """
    return {
        "status": status,
        "confidence": float(confidence),
        "reason": reason,
        "source": source,
        "suggestions": list(suggestions or []),
        "signals": dict(signals or {}),
    }


def make_interpretation_result(
    mode: str = "rule",
    text: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a normalized interpretation payload."""
    return {
        "mode": mode,
        "text": text,
        "provider": provider,
        "model": model,
        "error": error,
    }
