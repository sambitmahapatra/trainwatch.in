"""Summary generation for training runs."""

from typing import Any, Dict, List, Optional

from . import cloud as cloud_module
from . import config as config_module
from .contracts import make_interpretation_result
from . import llm as llm_module
from . import metrics as metrics_module
from . import rules
from . import suggestions as suggestions_module


def build_payload(
    state: Dict[str, Any],
    metrics: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the enriched Phase-02 payload used by summary/report flows."""
    payload = metrics_module.build_runtime_payload(state, metrics)
    analysis = suggestions_module.attach_suggestions(rules.analyze(payload))
    payload["analysis"] = analysis

    settings = config_module.get_interpretation_settings(config or {})
    mode = settings["mode"]
    payload["interpretation"] = make_interpretation_result(mode=mode)
    if payload.get("status") in {"completed", "failed"} and mode in {"llm", "hybrid"}:
        payload["interpretation"] = _resolve_interpretation(payload, analysis, settings)

    return payload


def generate(
    state: Dict[str, Any],
    metrics: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a concise summary for the training run."""
    return render_payload(build_payload(state, metrics, config=config))


def render_payload(payload: Dict[str, Any]) -> str:
    """Render summary text from an enriched payload."""
    status = payload.get("status", "unknown")
    if status == "completed":
        title = "Training Completed"
    elif status == "failed":
        title = "Training Failed"
    else:
        title = "Training Status"

    lines: List[str] = [title, ""]
    runtime_str = payload["runtime"]["human"]
    lines.append(f"Runtime: {runtime_str}")

    if status == "failed":
        error = payload.get("error", {})
        error_message = error.get("message") or error.get("type")
        if error_message:
            lines.append(f"Error: {error_message}")
        last_epoch = payload["progress"].get("epochs")
        if last_epoch is not None:
            lines.append(f"Last Epoch: {_format_epoch(last_epoch)}")
        analysis = payload.get("analysis") or suggestions_module.attach_suggestions(rules.analyze(payload))
        if analysis.get("reason"):
            lines.extend(["", f"Likely Cause: {analysis['reason']}"])
            if analysis.get("suggestions"):
                lines.append("")
                lines.append("Suggestions:")
                for suggestion in analysis["suggestions"][:3]:
                    lines.append(f"- {suggestion}")

        interpretation = payload.get("interpretation") or {}
        if interpretation.get("text"):
            lines.extend(["", "LLM Diagnosis:", str(interpretation["text"])])
        return "\n".join(lines)

    extra_lines: List[str] = []

    best_val_acc = payload["metrics"]["best"].get("val_accuracy")
    if best_val_acc is not None:
        extra_lines.append(f"Best Validation Accuracy: {_format_value(best_val_acc['value'])}")
        if best_val_acc.get("epoch") is not None:
            extra_lines.append(f"Epoch of Best Model: {_format_epoch(best_val_acc['epoch'])}")

    last_metrics = payload["metrics"].get("last") or {}
    final_loss = last_metrics.get("train_loss")
    if final_loss is not None:
        extra_lines.append(f"Final Loss: {_format_value(final_loss)}")

    final_acc = last_metrics.get("train_accuracy")
    if final_acc is not None:
        extra_lines.append(f"Final Accuracy: {_format_value(final_acc)}")

    last_epoch = payload["progress"].get("epochs")
    if last_epoch is not None and not _has_epoch_line(extra_lines):
        extra_lines.append(f"Epochs: {_format_epoch(last_epoch)}")

    if len(extra_lines) > 3:
        extra_lines = extra_lines[:3]

    lines.extend(extra_lines)

    best_model = payload.get("best_model")
    if isinstance(best_model, dict):
        best_model_lines = _format_best_model(best_model)
        if best_model_lines:
            lines.extend(["", *best_model_lines])

    analysis = payload.get("analysis") or suggestions_module.attach_suggestions(rules.analyze(payload))
    interpretation = payload.get("interpretation") or {}
    mode = interpretation.get("mode") or "rule"
    show_rule_observation = mode != "llm" or not interpretation.get("text")

    observation = analysis.get("reason")
    if show_rule_observation and observation and analysis.get("status") not in {"insufficient_data", "mixed_signal", "not_run"}:
        lines.extend(["", f"Observation: {observation}"])
        if analysis.get("suggestions"):
            lines.append("")
            lines.append("Suggestions:")
            for suggestion in analysis["suggestions"][:3]:
                lines.append(f"- {suggestion}")

    if interpretation.get("text"):
        lines.extend(["", "LLM Interpretation:", str(interpretation["text"])])

    return "\n".join(lines)


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


def _format_best_model(best_model: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    model_name = best_model.get("model")
    if model_name:
        lines.append(f"Best Model: {model_name}")
    score = best_model.get("score")
    if score is not None:
        lines.append(f"Best Score: {_format_value(score)}")
    params = best_model.get("params")
    if isinstance(params, dict) and params:
        ordered = sorted(params.items())[:3]
        rendered = ", ".join(f"{key}={value}" for key, value in ordered)
        lines.append(f"Best Params: {rendered}")
    return lines


def _resolve_interpretation(
    payload: Dict[str, Any],
    analysis: Dict[str, Any],
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    mode = settings.get("mode", "rule")
    fallback = settings.get("fallback", "rule")

    hosted_cfg = settings.get("hosted") or {}
    if hosted_cfg.get("enabled", True):
        try:
            interpretation = cloud_module.request_interpretation(
                payload,
                analysis,
                mode=mode,
                base_url=hosted_cfg.get("base_url"),
                api_key=hosted_cfg.get("api_key"),
                api_key_path=hosted_cfg.get("api_key_path"),
            )
            interpretation["provider"] = interpretation.get("provider") or "hosted"
            return interpretation
        except Exception as exc:
            hosted_error = str(exc)
        else:
            hosted_error = None
    else:
        hosted_error = "Hosted interpretation disabled."

    if fallback == "byok":
        byok_cfg = settings.get("byok") or {}
        try:
            interpretation = llm_module.interpret(payload, analysis, byok_cfg)
            interpretation["mode"] = mode
            return interpretation
        except Exception as exc:
            return make_interpretation_result(mode=mode, error=str(exc))

    if fallback == "none":
        return make_interpretation_result(mode=mode, error=hosted_error)

    return make_interpretation_result(mode=mode, error=hosted_error)
