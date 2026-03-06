"""Configuration loading and helpers."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional

from .exceptions import ConfigurationError
from .notifier import NotificationEngine
from .notifications.email_notifier import EmailNotifier
from .notifications.telegram_notifier import TelegramNotifier

DEFAULT_CONFIG_PATH = "trainwatcher_config.yaml"
CONFIG_ENV_VAR = "TRAINWATCHER_CONFIG"
LEGACY_CONFIG_ENV_VAR = "TRAINWATCH_CONFIG"
DEFAULT_RUN_LOG_PATH = "trainwatcher_run.json"


def resolve_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file and merge with environment overrides."""
    base = load_config(path)
    env = load_env_overrides()
    return deep_merge(base, env)


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from disk. Returns an empty dict if missing."""
    resolved = path or _get_env(CONFIG_ENV_VAR, LEGACY_CONFIG_ENV_VAR) or DEFAULT_CONFIG_PATH
    if not os.path.exists(resolved):
        return {}

    data = _load_file(resolved)
    if not isinstance(data, dict):
        raise ConfigurationError("Config file must contain a mapping at top level.")

    config = dict(data)
    meta = config.get("_meta") if isinstance(config.get("_meta"), dict) else {}
    meta = dict(meta)
    meta["source_path"] = resolved
    config["_meta"] = meta
    return config


def _load_file(path: str) -> Dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as handle:
        content = handle.read()

    if ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise ConfigurationError(
                "PyYAML is required to load YAML config files. "
                "Install with `pip install pyyaml` or use JSON."
            ) from exc
        data = yaml.safe_load(content) or {}
        if not isinstance(data, dict):
            raise ConfigurationError("YAML config must be a mapping at top level.")
        return data

    if ext == ".json":
        data = json.loads(content or "{}")
        if not isinstance(data, dict):
            raise ConfigurationError("JSON config must be a mapping at top level.")
        return data

    raise ConfigurationError(f"Unsupported config format: {ext}")


def load_env_overrides() -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}

    def set_path(path: Iterable[str], value: Any) -> None:
        if value is None:
            return
        current = overrides
        parts = list(path)
        for key in parts[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[parts[-1]] = value

    set_path(
        ["notifications", "email"],
        _coerce_bool(_get_env("TRAINWATCHER_NOTIFICATIONS_EMAIL", "TRAINWATCH_NOTIFICATIONS_EMAIL")),
    )
    set_path(
        ["notifications", "telegram"],
        _coerce_bool(_get_env("TRAINWATCHER_NOTIFICATIONS_TELEGRAM", "TRAINWATCH_NOTIFICATIONS_TELEGRAM")),
    )

    set_path(["email", "host"], _get_env("TRAINWATCHER_EMAIL_HOST", "TRAINWATCH_EMAIL_HOST"))
    set_path(["email", "port"], _coerce_int(_get_env("TRAINWATCHER_EMAIL_PORT", "TRAINWATCH_EMAIL_PORT")))
    set_path(["email", "username"], _get_env("TRAINWATCHER_EMAIL_USERNAME", "TRAINWATCH_EMAIL_USERNAME"))
    set_path(["email", "password"], _get_env("TRAINWATCHER_EMAIL_PASSWORD", "TRAINWATCH_EMAIL_PASSWORD"))
    set_path(["email", "sender"], _get_env("TRAINWATCHER_EMAIL_SENDER", "TRAINWATCH_EMAIL_SENDER"))
    set_path(["email", "recipient"], _get_env("TRAINWATCHER_EMAIL_RECIPIENT", "TRAINWATCH_EMAIL_RECIPIENT"))
    set_path(
        ["email", "use_tls"],
        _coerce_bool(_get_env("TRAINWATCHER_EMAIL_USE_TLS", "TRAINWATCH_EMAIL_USE_TLS")),
    )
    set_path(["email", "subject"], _get_env("TRAINWATCHER_EMAIL_SUBJECT", "TRAINWATCH_EMAIL_SUBJECT"))

    set_path(["telegram", "bot_token"], _get_env("TRAINWATCHER_TELEGRAM_BOT_TOKEN", "TRAINWATCH_TELEGRAM_BOT_TOKEN"))
    set_path(["telegram", "chat_id"], _get_env("TRAINWATCHER_TELEGRAM_CHAT_ID", "TRAINWATCH_TELEGRAM_CHAT_ID"))

    set_path(
        ["logging", "enabled"],
        _coerce_bool(_get_env("TRAINWATCHER_LOGGING_ENABLED", "TRAINWATCH_LOGGING_ENABLED")),
    )
    set_path(["logging", "path"], _get_env("TRAINWATCHER_LOGGING_PATH", "TRAINWATCH_LOGGING_PATH"))
    set_path(["interpretation", "mode"], _get_env("TRAINWATCHER_INTERPRETATION_MODE"))
    set_path(
        ["interpretation", "fallback"],
        _get_env("TRAINWATCHER_INTERPRETATION_FALLBACK", "TRAINWATCHER_LLM_FALLBACK"),
    )
    set_path(
        ["interpretation", "byok", "provider"],
        _get_env("TRAINWATCHER_LLM_PROVIDER"),
    )
    set_path(
        ["interpretation", "byok", "api_key"],
        _get_env("TRAINWATCHER_LLM_API_KEY"),
    )
    set_path(
        ["interpretation", "byok", "base_url"],
        _get_env("TRAINWATCHER_LLM_BASE_URL"),
    )
    set_path(
        ["interpretation", "byok", "model"],
        _get_env("TRAINWATCHER_LLM_MODEL"),
    )
    set_path(
        ["interpretation", "byok", "max_tokens"],
        _coerce_int(_get_env("TRAINWATCHER_LLM_MAX_TOKENS")),
    )
    set_path(
        ["interpretation", "byok", "temperature"],
        _coerce_float(_get_env("TRAINWATCHER_LLM_TEMPERATURE")),
    )
    set_path(
        ["interpretation", "byok", "timeout_seconds"],
        _coerce_int(_get_env("TRAINWATCHER_LLM_TIMEOUT_SECONDS")),
    )

    return overrides


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_enabled_channels(config: Dict[str, Any]) -> list[str]:
    notifications = _get_dict(config, "notifications")
    channels: list[str] = []
    if _coerce_bool(notifications.get("email", False)):
        channels.append("email")
    if _coerce_bool(notifications.get("telegram", False)):
        channels.append("telegram")
    return channels


def build_notification_engine(config: Dict[str, Any]) -> NotificationEngine:
    channels = set(get_enabled_channels(config))
    email_notifier = _build_email_notifier(_get_dict(config, "email")) if "email" in channels else None
    telegram_notifier = (
        _build_telegram_notifier(_get_dict(config, "telegram")) if "telegram" in channels else None
    )
    return NotificationEngine(email=email_notifier, telegram=telegram_notifier)


def get_logging_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    logging_cfg = _get_dict(config, "logging")
    enabled = _coerce_bool(logging_cfg.get("enabled", False))
    path = logging_cfg.get("path") or DEFAULT_RUN_LOG_PATH
    return {"enabled": enabled, "path": path}


def get_interpretation_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    interpretation = _get_dict(config, "interpretation")
    mode = str(interpretation.get("mode") or "rule").strip().lower()
    if mode not in {"rule", "llm", "hybrid"}:
        mode = "rule"
    fallback = str(interpretation.get("fallback") or "rule").strip().lower()
    if fallback not in {"rule", "byok", "none"}:
        fallback = "rule"

    hosted_cfg = _get_dict(interpretation, "hosted")
    hosted_enabled = hosted_cfg.get("enabled")
    if hosted_enabled is None:
        hosted_cfg["enabled"] = True
    else:
        hosted_cfg["enabled"] = bool(_coerce_bool(hosted_enabled))

    byok_cfg = _get_dict(interpretation, "byok")
    if not byok_cfg and isinstance(interpretation.get("llm"), dict):
        byok_cfg = _get_dict(interpretation, "llm")

    return {
        "mode": mode,
        "fallback": fallback,
        "hosted": hosted_cfg,
        "byok": byok_cfg,
    }


def resolve_path(config: Dict[str, Any], path: str) -> str:
    if os.path.isabs(path):
        return path
    source = _get_source_path(config)
    base_dir = os.path.dirname(source) if source else os.getcwd()
    return os.path.join(base_dir, path)


def _get_dict(config: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = config.get(key)
    return value if isinstance(value, dict) else {}


def _get_source_path(config: Dict[str, Any]) -> Optional[str]:
    meta = config.get("_meta")
    if isinstance(meta, dict):
        return meta.get("source_path")
    return None


def _build_email_notifier(email_cfg: Dict[str, Any]) -> EmailNotifier:
    host = email_cfg.get("host")
    sender = email_cfg.get("sender")
    recipient = email_cfg.get("recipient")
    port = _coerce_int(email_cfg.get("port")) or 587
    use_tls = _coerce_bool(email_cfg.get("use_tls", True))
    subject = email_cfg.get("subject") or "TrainWatcher Notification"

    if not host or not sender or not recipient:
        raise ConfigurationError("Email config requires host, sender, and recipient.")

    return EmailNotifier(
        host=host,
        port=port,
        username=email_cfg.get("username"),
        password=email_cfg.get("password"),
        sender=sender,
        recipient=recipient,
        use_tls=use_tls,
        subject=subject,
    )


def _build_telegram_notifier(telegram_cfg: Dict[str, Any]) -> TelegramNotifier:
    bot_token = telegram_cfg.get("bot_token")
    chat_id = telegram_cfg.get("chat_id")
    api_base = telegram_cfg.get("api_base") or "https://api.telegram.org"

    if not bot_token or not chat_id:
        raise ConfigurationError("Telegram config requires bot_token and chat_id.")

    return TelegramNotifier(bot_token=bot_token, chat_id=chat_id, api_base=api_base)


def _coerce_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return bool(value)


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_env(name: str, legacy: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None and legacy:
        value = os.getenv(legacy)
    return value
