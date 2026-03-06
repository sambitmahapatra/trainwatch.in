"""Deterministic rule-based analysis for training behavior."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .contracts import make_analysis_result


def analyze(
    payload: Dict[str, Any],
    *,
    plateau_delta: float = 0.005,
    plateau_patience: int = 3,
    divergence_patience: int = 3,
    overfit_window: int = 3,
) -> Dict[str, Any]:
    """Analyze normalized runtime payload and detect common training patterns."""
    if payload.get("status") == "failed":
        return _detect_failure(payload)

    series = payload.get("metrics", {}).get("series", {})
    train_loss = _series_values(series.get("train_loss"))
    val_loss = _series_values(series.get("val_loss"))
    train_accuracy = _series_values(series.get("train_accuracy"))
    val_accuracy = _series_values(series.get("val_accuracy"))

    available = [
        name
        for name, values in (
            ("train_loss", train_loss),
            ("val_loss", val_loss),
            ("train_accuracy", train_accuracy),
            ("val_accuracy", val_accuracy),
        )
        if values
    ]
    if not available or max(len(values) for values in (train_loss, val_loss, train_accuracy, val_accuracy) if values) < 2:
        return make_analysis_result(
            status="insufficient_data",
            confidence=0.0,
            reason="Need at least two metric points to analyze training behavior.",
            signals={"available_metrics": available},
        )

    diverging = _detect_divergence(train_loss, val_loss, divergence_patience)
    if diverging is not None:
        return diverging

    overfitting = _detect_overfitting(train_loss, val_loss, train_accuracy, val_accuracy, overfit_window)
    if overfitting is not None:
        return overfitting

    plateau = _detect_plateau(train_loss, val_loss, train_accuracy, val_accuracy, plateau_delta, plateau_patience)
    if plateau is not None:
        return plateau

    convergence = _detect_normal_convergence(train_loss, val_loss, train_accuracy, val_accuracy, overfit_window)
    if convergence is not None:
        return convergence

    return make_analysis_result(
        status="mixed_signal",
        confidence=0.4,
        reason="Metrics do not match a strong rule pattern yet.",
        signals={"available_metrics": available},
    )


def _detect_failure(payload: Dict[str, Any]) -> Dict[str, Any]:
    error = payload.get("error") or {}
    error_type = str(error.get("type") or "").strip()
    error_message = str(error.get("message") or "").strip()
    lowered = f"{error_type} {error_message}".lower()

    if "target" in lowered and "out of bounds" in lowered:
        return make_analysis_result(
            status="class_index_mismatch",
            confidence=0.98,
            reason=(
                "The target labels exceed the model output dimension, which usually means "
                "the final layer class count does not match the dataset labels."
            ),
            signals={"error_type": error_type, "error_message": error_message},
        )

    if "cuda" in lowered and "out of memory" in lowered:
        return make_analysis_result(
            status="cuda_oom",
            confidence=0.97,
            reason=(
                "The run exhausted available GPU memory before the step could complete."
            ),
            signals={"error_type": error_type, "error_message": error_message},
        )

    if "device-side assert triggered" in lowered:
        return make_analysis_result(
            status="cuda_device_assert",
            confidence=0.9,
            reason=(
                "A CUDA device-side assertion was triggered, commonly caused by invalid "
                "class indices, illegal indexing, or an earlier tensor shape error."
            ),
            signals={"error_type": error_type, "error_message": error_message},
        )

    if "mat1 and mat2 shapes cannot be multiplied" in lowered or "size mismatch" in lowered:
        return make_analysis_result(
            status="shape_mismatch",
            confidence=0.94,
            reason=(
                "A tensor shape mismatch occurred between layers or between the model "
                "output and the expected input shape."
            ),
            signals={"error_type": error_type, "error_message": error_message},
        )

    if "expected all tensors to be on the same device" in lowered:
        return make_analysis_result(
            status="device_mismatch",
            confidence=0.95,
            reason=(
                "Model parameters and input tensors were placed on different devices."
            ),
            signals={"error_type": error_type, "error_message": error_message},
        )

    if "no such file or directory" in lowered or "filenotfounderror" in lowered:
        return make_analysis_result(
            status="missing_file",
            confidence=0.95,
            reason=(
                "A required file or dataset path could not be found at runtime."
            ),
            signals={"error_type": error_type, "error_message": error_message},
        )

    if "modulenotfounderror" in lowered or "no module named" in lowered:
        return make_analysis_result(
            status="dependency_error",
            confidence=0.92,
            reason=(
                "A required Python dependency is missing from the current environment."
            ),
            signals={"error_type": error_type, "error_message": error_message},
        )

    label = error_type or "training"
    return make_analysis_result(
        status="runtime_error",
        confidence=0.35,
        reason=(
            f"The run failed with {label}. Review the stack trace and the recent metrics "
            "to isolate the root cause."
        ),
        signals={"error_type": error_type, "error_message": error_message},
    )


def attach_analysis(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """Return a copy of the payload with deterministic analysis attached."""
    enriched = dict(payload)
    enriched["analysis"] = analyze(payload, **kwargs)
    return enriched


def _detect_divergence(
    train_loss: List[float],
    val_loss: List[float],
    patience: int,
) -> Optional[Dict[str, Any]]:
    metric_candidates: List[Tuple[str, List[float]]] = [("train_loss", train_loss)]
    if not train_loss:
        metric_candidates.append(("val_loss", val_loss))

    for metric_name, values in metric_candidates:
        window = _tail(values, patience + 1)
        if len(window) < patience + 1:
            continue
        if _strictly_increasing(window):
            delta = window[-1] - window[0]
            if delta > 0.01:
                confidence = min(0.95, 0.6 + delta)
                return make_analysis_result(
                    status="diverging",
                    confidence=confidence,
                    reason=f"{metric_name} increased consistently over the last {patience} intervals.",
                    signals={"metric": metric_name, "delta": delta, "window": window},
                )
    return None


def _detect_overfitting(
    train_loss: List[float],
    val_loss: List[float],
    train_accuracy: List[float],
    val_accuracy: List[float],
    window: int,
) -> Optional[Dict[str, Any]]:
    loss_window = min(len(train_loss), len(val_loss), window + 1)
    if loss_window >= window + 1:
        train_tail = _tail(train_loss, loss_window)
        val_tail = _tail(val_loss, loss_window)
        train_delta = train_tail[0] - train_tail[-1]
        val_delta = val_tail[-1] - val_tail[0]
        if train_delta > 0.01 and val_delta > 0.01:
            confidence = min(0.95, 0.65 + train_delta + val_delta)
            return make_analysis_result(
                status="overfitting",
                confidence=confidence,
                reason="Training loss improved while validation loss worsened.",
                signals={
                    "train_loss_delta": train_delta,
                    "val_loss_delta": val_delta,
                    "window": loss_window,
                },
            )

    acc_window = min(len(train_accuracy), len(val_accuracy), window + 1)
    if acc_window >= window + 1:
        train_tail = _tail(train_accuracy, acc_window)
        val_tail = _tail(val_accuracy, acc_window)
        train_delta = train_tail[-1] - train_tail[0]
        val_delta = val_tail[-1] - val_tail[0]
        if train_delta > 0.01 and val_delta < -0.01:
            confidence = min(0.95, 0.6 + train_delta + abs(val_delta))
            return make_analysis_result(
                status="overfitting",
                confidence=confidence,
                reason="Training accuracy improved while validation accuracy declined.",
                signals={
                    "train_accuracy_delta": train_delta,
                    "val_accuracy_delta": val_delta,
                    "window": acc_window,
                },
            )

    return None


def _detect_plateau(
    train_loss: List[float],
    val_loss: List[float],
    train_accuracy: List[float],
    val_accuracy: List[float],
    delta: float,
    patience: int,
) -> Optional[Dict[str, Any]]:
    metric_candidates: List[Tuple[str, List[float], str]] = [
        ("val_loss", val_loss, "min"),
        ("val_accuracy", val_accuracy, "max"),
        ("train_loss", train_loss, "min"),
        ("train_accuracy", train_accuracy, "max"),
    ]
    for metric_name, values, mode in metric_candidates:
        window = _tail(values, patience + 1)
        if len(window) < patience + 1:
            continue
        improvement = _improvement(window, mode)
        if improvement <= delta:
            confidence = min(0.9, 0.55 + max(0.0, delta - improvement))
            return make_analysis_result(
                status="plateau",
                confidence=confidence,
                reason=f"{metric_name} showed limited improvement over the last {patience} intervals.",
                signals={"metric": metric_name, "improvement": improvement, "window": window},
            )
    return None


def _detect_normal_convergence(
    train_loss: List[float],
    val_loss: List[float],
    train_accuracy: List[float],
    val_accuracy: List[float],
    window: int,
) -> Optional[Dict[str, Any]]:
    loss_window = min(len(train_loss), len(val_loss), window + 1)
    if loss_window >= window + 1:
        train_tail = _tail(train_loss, loss_window)
        val_tail = _tail(val_loss, loss_window)
        train_improvement = train_tail[0] - train_tail[-1]
        val_improvement = val_tail[0] - val_tail[-1]
        if train_improvement > 0.01 and val_improvement > 0.01:
            confidence = min(0.95, 0.65 + train_improvement + val_improvement)
            return make_analysis_result(
                status="normal_convergence",
                confidence=confidence,
                reason="Training and validation loss both improved over the recent window.",
                signals={
                    "train_loss_delta": train_improvement,
                    "val_loss_delta": val_improvement,
                    "window": loss_window,
                },
            )

    acc_window = min(len(train_accuracy), len(val_accuracy), window + 1)
    if acc_window >= window + 1:
        train_tail = _tail(train_accuracy, acc_window)
        val_tail = _tail(val_accuracy, acc_window)
        train_improvement = train_tail[-1] - train_tail[0]
        val_improvement = val_tail[-1] - val_tail[0]
        if train_improvement > 0.01 and val_improvement > 0.01:
            confidence = min(0.95, 0.65 + train_improvement + val_improvement)
            return make_analysis_result(
                status="normal_convergence",
                confidence=confidence,
                reason="Training and validation accuracy both improved over the recent window.",
                signals={
                    "train_accuracy_delta": train_improvement,
                    "val_accuracy_delta": val_improvement,
                    "window": acc_window,
                },
            )

    return None


def _series_values(points: Optional[List[Dict[str, Any]]]) -> List[float]:
    if not points:
        return []
    return [float(point["value"]) for point in points if "value" in point]


def _tail(values: List[float], size: int) -> List[float]:
    return values[-size:] if size > 0 else []


def _strictly_increasing(values: List[float]) -> bool:
    return all(curr > prev for prev, curr in zip(values, values[1:]))


def _improvement(values: List[float], mode: str) -> float:
    if len(values) < 2:
        return 0.0
    if mode == "min":
        return values[0] - values[-1]
    return values[-1] - values[0]
