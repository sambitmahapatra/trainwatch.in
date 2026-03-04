"""Configuration loading and helpers."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional

from .exceptions import ConfigurationError
from .notifier import NotificationEngine
from .notifications.email_notifier import EmailNotifier
from .notifications.telegram_notifier import TelegramNotifier

DEFAULT_CONFIG_PATH = "trainwatch_config.yaml"
CONFIG_ENV_VAR = "TRAINWATCH_CONFIG"
DEFAULT_RUN_LOG_PATH = "trainwatch_run.json"


def resolve_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file and merge with environment overrides."""
    base = load_config(path)
    env = load_env_overrides()
    return deep_merge(base, env)


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from disk. Returns an empty dict if missing."""
    resolved = path or os.getenv(CONFIG_ENV_VAR) or DEFAULT_CONFIG_PATH
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

    set_path(["notifications", "email"], _coerce_bool(os.getenv("TRAINWATCH_NOTIFICATIONS_EMAIL")))
    set_path(["notifications", "telegram"], _coerce_bool(os.getenv("TRAINWATCH_NOTIFICATIONS_TELEGRAM")))

    set_path(["email", "host"], os.getenv("TRAINWATCH_EMAIL_HOST"))
    set_path(["email", "port"], _coerce_int(os.getenv("TRAINWATCH_EMAIL_PORT")))
    set_path(["email", "username"], os.getenv("TRAINWATCH_EMAIL_USERNAME"))
    set_path(["email", "password"], os.getenv("TRAINWATCH_EMAIL_PASSWORD"))
    set_path(["email", "sender"], os.getenv("TRAINWATCH_EMAIL_SENDER"))
    set_path(["email", "recipient"], os.getenv("TRAINWATCH_EMAIL_RECIPIENT"))
    set_path(["email", "use_tls"], _coerce_bool(os.getenv("TRAINWATCH_EMAIL_USE_TLS")))
    set_path(["email", "subject"], os.getenv("TRAINWATCH_EMAIL_SUBJECT"))

    set_path(["telegram", "bot_token"], os.getenv("TRAINWATCH_TELEGRAM_BOT_TOKEN"))
    set_path(["telegram", "chat_id"], os.getenv("TRAINWATCH_TELEGRAM_CHAT_ID"))

    set_path(["logging", "enabled"], _coerce_bool(os.getenv("TRAINWATCH_LOGGING_ENABLED")))
    set_path(["logging", "path"], os.getenv("TRAINWATCH_LOGGING_PATH"))

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
    subject = email_cfg.get("subject") or "TrainWatch Notification"

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
