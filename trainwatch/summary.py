"""Summary generation for training runs."""

from typing import Any, Dict, Iterable, List, Optional, Tuple

from .utils.time_utils import format_duration


Numeric = float


def generate(state: Dict[str, Any], metrics: List[Dict[str, Any]]) -> str:
    """Generate a concise summary for the training run."""
    status = state.get("status", "unknown")
    if status == "completed":
        title = "Training Completed"
    elif status == "failed":
        title = "Training Failed"
    else:
        title = "Training Status"

    lines: List[str] = [title, ""]
    runtime_str = format_duration(state.get("runtime_seconds"))
    lines.append(f"Runtime: {runtime_str}")

    if status == "failed":
        error_message = state.get("error_message") or state.get("error_type")
        if error_message:
            lines.append(f"Error: {error_message}")
        last_epoch = _extract_last_epoch(metrics)
        if last_epoch is not None:
            lines.append(f"Last Epoch: {_format_epoch(last_epoch)}")
        return "\n".join(lines)

    extra_lines: List[str] = []

    best_val_acc, best_epoch, _ = _extract_best(metrics, ["val_acc", "val_accuracy"])
    if best_val_acc is not None:
        extra_lines.append(f"Best Validation Accuracy: {_format_value(best_val_acc)}")
        if best_epoch is not None:
            extra_lines.append(f"Epoch of Best Model: {_format_epoch(best_epoch)}")

    final_loss, loss_key = _extract_last_value(metrics, ["loss", "train_loss"])
    if final_loss is not None:
        label = "Final Loss" if loss_key in ("loss", "train_loss") else "Final Loss"
        extra_lines.append(f"{label}: {_format_value(final_loss)}")

    final_acc, _ = _extract_last_value(metrics, ["accuracy", "acc"])
    if final_acc is not None:
        extra_lines.append(f"Final Accuracy: {_format_value(final_acc)}")

    last_epoch = _extract_last_epoch(metrics)
    if last_epoch is not None and not _has_epoch_line(extra_lines):
        extra_lines.append(f"Epochs: {_format_epoch(last_epoch)}")

    if len(extra_lines) > 3:
        extra_lines = extra_lines[:3]

    lines.extend(extra_lines)
    return "\n".join(lines)


def _extract_best(metrics: List[Dict[str, Any]], keys: Iterable[str]) -> Tuple[Optional[Numeric], Optional[Any], Optional[str]]:
    best_val: Optional[Numeric] = None
    best_epoch: Optional[Any] = None
    best_key: Optional[str] = None

    for entry in metrics:
        value, key = _extract_first(entry, keys)
        if value is None:
            continue
        numeric = _to_numeric(value)
        if numeric is None:
            continue
        if best_val is None or numeric > best_val:
            best_val = numeric
            best_key = key
            best_epoch = entry.get("epoch")

    return best_val, best_epoch, best_key


def _extract_last_value(metrics: List[Dict[str, Any]], keys: Iterable[str]) -> Tuple[Optional[Any], Optional[str]]:
    for entry in reversed(metrics):
        value, key = _extract_first(entry, keys)
        if value is not None:
            return value, key
    return None, None


def _extract_first(entry: Dict[str, Any], keys: Iterable[str]) -> Tuple[Optional[Any], Optional[str]]:
    for key in keys:
        if key in entry:
            return entry.get(key), key
    return None, None


def _extract_last_epoch(metrics: List[Dict[str, Any]]) -> Optional[Any]:
    for entry in reversed(metrics):
        if "epoch" in entry:
            return entry.get("epoch")
    return None


def _to_numeric(value: Any) -> Optional[Numeric]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _format_epoch(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _has_epoch_line(lines: List[str]) -> bool:
    return any(line.startswith("Epoch") for line in lines)
