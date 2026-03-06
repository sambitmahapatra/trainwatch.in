"""Optional OpenAI-compatible BYOK interpretation helpers."""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, Optional

from .contracts import make_interpretation_result
from .exceptions import TrainWatcherError
from . import prompts

DEFAULT_PROVIDER = "openai_compat"
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_MAX_TOKENS = 300
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TIMEOUT_SECONDS = 20


def interpret(
    payload: Dict[str, Any],
    analysis: Dict[str, Any],
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call an OpenAI-compatible API and return concise interpretation text."""
    settings = resolve_config(llm_config)
    if not settings.get("api_key"):
        raise TrainWatcherError("LLM API key is required for interpretation mode.")

    url = settings["base_url"].rstrip("/") + "/chat/completions"
    body = {
        "model": settings["model"],
        "messages": prompts.build_messages(payload, analysis),
        "temperature": settings["temperature"],
        "max_tokens": settings["max_tokens"],
    }
    response = _post_json(url, body, api_key=settings["api_key"], timeout=settings["timeout_seconds"])
    text = _extract_text(response)
    if not text:
        raise TrainWatcherError("LLM response did not include any interpretation text.")

    return make_interpretation_result(
        mode="llm",
        text=text,
        provider=settings["provider"],
        model=settings["model"],
        error=None,
    )


def resolve_config(raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Resolve LLM config with OpenAI-compatible defaults."""
    config = dict(raw or {})
    base_url = str(config.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
    model = str(config.get("model") or DEFAULT_MODEL)
    provider = str(config.get("provider") or _infer_provider(base_url))

    return {
        "provider": provider,
        "api_key": config.get("api_key"),
        "base_url": base_url,
        "model": model,
        "max_tokens": _coerce_int(config.get("max_tokens")) or DEFAULT_MAX_TOKENS,
        "temperature": _coerce_float(config.get("temperature"))
        if _coerce_float(config.get("temperature")) is not None
        else DEFAULT_TEMPERATURE,
        "timeout_seconds": _coerce_int(config.get("timeout_seconds")) or DEFAULT_TIMEOUT_SECONDS,
    }


def _post_json(url: str, payload: Dict[str, Any], *, api_key: str, timeout: int) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("User-Agent", "TrainWatcher/0.2")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as exc:
        raise TrainWatcherError(f"LLM request failed: {exc}") from exc

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise TrainWatcherError("LLM response was not valid JSON.") from exc

    if isinstance(data, dict) and data.get("error"):
        raise TrainWatcherError(str(data["error"]))
    if not isinstance(data, dict):
        raise TrainWatcherError("LLM response payload was not a JSON object.")
    return data


def _extract_text(response: Dict[str, Any]) -> Optional[str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return str(content).strip() if content else None


def _infer_provider(base_url: str) -> str:
    if "groq.com" in base_url:
        return "groq"
    if "openrouter.ai" in base_url:
        return "openrouter"
    return DEFAULT_PROVIDER


def _coerce_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
