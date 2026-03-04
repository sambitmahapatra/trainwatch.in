"""Core monitoring entry points."""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import threading
import time
import warnings
from typing import Optional, Dict, Any, List

from .runtime import RuntimeTracker
from . import logger
from . import summary as summary_module
from . import config as config_module
from .exceptions import MonitorError, NotificationError, TrainWatchError
from . import cloud as cloud_module
from .utils.error_utils import stringify_exception


@dataclass
class MonitorState:
    status: str = "idle"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    runtime_seconds: Optional[float] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    summary: Optional[str] = None
    run_log_path: Optional[str] = None


_state = MonitorState()
_runtime = RuntimeTracker()
_heartbeat_thread: Optional[threading.Thread] = None
_heartbeat_stop: Optional[threading.Event] = None
_heartbeat_interval: Optional[float] = None
_heartbeat_message: str = "Training still running"
_heartbeat_subject: Optional[str] = None
_heartbeat_config: Optional[Dict[str, Any]] = None

_step_count: int = 0
_step_notify_every: Optional[int] = None
_step_message: str = "Training still running"
_step_subject: Optional[str] = None
_step_config: Optional[Dict[str, Any]] = None

_last_sent_at: Dict[str, float] = {}


def reset() -> None:
    """Reset the monitor to its initial state."""
    global _state, _runtime
    _state = MonitorState()
    _runtime = RuntimeTracker()
    logger.reset()
    _reset_heartbeat()
    _reset_steps()
    _last_sent_at.clear()


def start() -> Dict[str, Any]:
    """Start monitoring a training run."""
    if _state.status == "running":
        raise MonitorError("TrainWatch monitor already running.")

    logger.reset()
    _runtime.start()
    _state.status = "running"
    _state.start_time = datetime.now(timezone.utc)
    _state.end_time = None
    _state.runtime_seconds = None
    _state.error_type = None
    _state.error_message = None
    _state.summary = None
    _state.run_log_path = None
    _reset_steps()
    _warn_if_notifications_disabled()

    return snapshot()


@contextmanager
def watch(config: Optional[Dict[str, Any]] = None):
    """Context manager that automatically calls end() or fail()."""
    start()
    try:
        yield snapshot()
    except Exception as exc:
        try:
            fail(exc, config=config)
        finally:
            raise
    else:
        end(config=config)


def log(**metrics: Any) -> Dict[str, Any]:
    """Log metrics for the current training run."""
    return logger.log(**metrics)


def configure(
    heartbeat_interval: Optional[float] = None,
    heartbeat_message: Optional[str] = None,
    heartbeat_subject: Optional[str] = None,
    step_notify_every: Optional[int] = None,
    step_message: Optional[str] = None,
    step_subject: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Set default settings for heartbeat/step notifications."""
    global _heartbeat_interval, _heartbeat_message, _heartbeat_subject, _heartbeat_config
    global _step_notify_every, _step_message, _step_subject, _step_config

    if heartbeat_interval is not None:
        if heartbeat_interval <= 0:
            raise MonitorError("heartbeat_interval must be positive.")
        _heartbeat_interval = float(heartbeat_interval)
    if heartbeat_message is not None:
        _heartbeat_message = heartbeat_message
    if heartbeat_subject is not None:
        _heartbeat_subject = heartbeat_subject
    if config is not None:
        _heartbeat_config = config

    if step_notify_every is not None:
        if step_notify_every <= 0:
            raise MonitorError("step_notify_every must be positive.")
        _step_notify_every = int(step_notify_every)
    if step_message is not None:
        _step_message = step_message
    if step_subject is not None:
        _step_subject = step_subject
    if config is not None:
        _step_config = config


def notify(message: str, subject: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> None:
    """Send a manual notification message."""
    resolved_config = _resolve_config(config)
    _maybe_send_notifications(resolved_config, message, subject=subject)


def heartbeat(
    interval_seconds: Optional[float] = None,
    message: Optional[str] = None,
    subject: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Send periodic heartbeat notifications until stopped."""
    global _heartbeat_interval, _heartbeat_message, _heartbeat_subject, _heartbeat_config, _heartbeat_stop, _heartbeat_thread
    if _state.status != "running":
        raise MonitorError("TrainWatch monitor is not running.")
    interval = _heartbeat_interval if interval_seconds is None else float(interval_seconds)
    if interval <= 0:
        raise MonitorError("interval_seconds must be positive.")

    _stop_heartbeat()
    _heartbeat_interval = interval
    _heartbeat_message = message if message is not None else _heartbeat_message
    _heartbeat_subject = subject if subject is not None else _heartbeat_subject
    _heartbeat_config = config if config is not None else _heartbeat_config
    _heartbeat_stop = threading.Event()
    _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    _heartbeat_thread.start()


def stop_heartbeat() -> None:
    """Stop any active heartbeat thread."""
    _stop_heartbeat()


def step(
    notify_every: Optional[int] = None,
    message: Optional[str] = None,
    subject: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> int:
    """Increment a step counter and optionally notify every N steps."""
    if _state.status != "running":
        raise MonitorError("TrainWatch monitor is not running.")

    global _step_count, _step_notify_every, _step_message, _step_subject, _step_config

    if notify_every is not None:
        if notify_every <= 0:
            raise MonitorError("notify_every must be positive.")
        _step_notify_every = int(notify_every)
    if message is not None:
        _step_message = message
    if subject is not None:
        _step_subject = subject
    if config is not None:
        _step_config = config

    _step_count += 1

    every = _step_notify_every if notify_every is None else int(notify_every)
    if every and (_step_count % every == 0):
        notify(
            message or _step_message,
            subject=subject or _step_subject,
            config=config or _step_config,
        )

    return _step_count


def end(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """End monitoring and mark the run as completed."""
    if _state.status != "running":
        raise MonitorError("TrainWatch monitor is not running.")

    _state.end_time = datetime.now(timezone.utc)
    _state.runtime_seconds = _runtime.stop()
    _state.status = "completed"

    summary_text = summary_module.generate(snapshot(), logger.get_metrics())
    _state.summary = summary_text

    resolved_config = _resolve_config(config)
    _state.run_log_path = _maybe_write_run_log(resolved_config)
    _maybe_send_notifications(resolved_config, summary_text)
    _stop_heartbeat()

    return snapshot()


def fail(exc: Optional[Exception], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """End monitoring and mark the run as failed."""
    if _state.status != "running":
        _runtime.start()
        _state.start_time = datetime.now(timezone.utc)

    _state.end_time = datetime.now(timezone.utc)
    _state.runtime_seconds = _runtime.stop()
    _state.status = "failed"

    exc_type, exc_message = stringify_exception(exc)
    _state.error_type = exc_type
    _state.error_message = exc_message

    summary_text = summary_module.generate(snapshot(), logger.get_metrics())
    _state.summary = summary_text

    resolved_config = _resolve_config(config)
    _state.run_log_path = _maybe_write_run_log(resolved_config)
    _maybe_send_notifications(resolved_config, summary_text)
    _stop_heartbeat()

    return snapshot()


def snapshot() -> Dict[str, Any]:
    """Return a snapshot of the current monitor state."""
    return {
        "status": _state.status,
        "start_time": _state.start_time,
        "end_time": _state.end_time,
        "runtime_seconds": _state.runtime_seconds,
        "error_type": _state.error_type,
        "error_message": _state.error_message,
        "summary": _state.summary,
        "run_log_path": _state.run_log_path,
    }


def get_state() -> MonitorState:
    """Return the internal monitor state object."""
    return _state


def is_running() -> bool:
    return _state.status == "running"


def _resolve_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if config is not None:
        return config
    return config_module.resolve_config()


def _warn_if_notifications_disabled() -> None:
    try:
        config = config_module.resolve_config()
    except Exception:
        return

    channels = config_module.get_enabled_channels(config)
    cloud_cfg = config.get("cloud") if isinstance(config.get("cloud"), dict) else {}
    cloud_enabled = cloud_cfg.get("enabled")
    if cloud_enabled is None:
        cloud_enabled = cloud_module.credentials_available(cloud_cfg.get("api_key_path"))

    if not channels and not cloud_enabled:
        warnings.warn(
            "TrainWatch: no notification channels enabled and no cloud credentials found; "
            "notifications will be skipped.",
            stacklevel=2,
        )


def _maybe_send_notifications(
    config: Dict[str, Any],
    message: str,
    subject: Optional[str] = None,
) -> None:
    errors = []

    channels = config_module.get_enabled_channels(config)
    allowed_channels = _filter_channels_by_limits(config, channels)
    if allowed_channels:
        engine = config_module.build_notification_engine(config)
        if engine.available_channels():
            try:
                attempted = engine.send(message, channels=allowed_channels)
                _mark_sent(attempted)
            except Exception as exc:
                errors.append(exc)

    cloud_cfg = config.get("cloud") if isinstance(config.get("cloud"), dict) else {}
    cloud_enabled = cloud_cfg.get("enabled")
    if cloud_enabled is None:
        cloud_enabled = cloud_module.credentials_available(cloud_cfg.get("api_key_path"))

    if cloud_enabled:
        if _should_send("cloud", _get_limit_seconds(config, "cloud_min_interval_seconds")):
            try:
                cloud_module.send_notification(
                    message,
                    subject=subject or cloud_cfg.get("subject"),
                    base_url=cloud_cfg.get("base_url"),
                    api_key=cloud_cfg.get("api_key"),
                    api_key_path=cloud_cfg.get("api_key_path"),
                )
                _mark_sent(["cloud"])
            except Exception as exc:
                errors.append(exc)

    if errors:
        raise NotificationError("Failed to send notification.") from errors[0]


def _filter_channels_by_limits(config: Dict[str, Any], channels: List[str]) -> List[str]:
    allowed: List[str] = []
    for channel in channels:
        limit_key = f"{channel}_min_interval_seconds"
        if _should_send(channel, _get_limit_seconds(config, limit_key)):
            allowed.append(channel)
    return allowed


def _get_limit_seconds(config: Dict[str, Any], key: str) -> Optional[float]:
    limits = config.get("limits") if isinstance(config.get("limits"), dict) else {}
    value = limits.get(key)
    if value is None:
        return None
    try:
        seconds = float(value)
        return seconds if seconds > 0 else None
    except (TypeError, ValueError):
        return None


def _should_send(channel: str, min_interval: Optional[float]) -> bool:
    if not min_interval:
        return True
    last = _last_sent_at.get(channel)
    if last is None:
        return True
    return (time.time() - last) >= min_interval


def _mark_sent(channels: List[str]) -> None:
    now = time.time()
    for channel in channels:
        _last_sent_at[channel] = now


def _heartbeat_loop() -> None:
    if _heartbeat_stop is None or _heartbeat_interval is None:
        return
    while not _heartbeat_stop.wait(_heartbeat_interval):
        try:
            notify(_heartbeat_message, subject=_heartbeat_subject, config=_heartbeat_config)
        except Exception:
            continue


def _stop_heartbeat() -> None:
    global _heartbeat_thread, _heartbeat_stop
    if _heartbeat_stop is not None:
        _heartbeat_stop.set()
    if _heartbeat_thread is not None and _heartbeat_thread.is_alive():
        _heartbeat_thread.join(timeout=1)
    _heartbeat_thread = None
    _heartbeat_stop = None


def _reset_heartbeat() -> None:
    global _heartbeat_interval, _heartbeat_message, _heartbeat_subject, _heartbeat_config
    _stop_heartbeat()
    _heartbeat_interval = None
    _heartbeat_message = "Training still running"
    _heartbeat_subject = None
    _heartbeat_config = None


def _reset_steps() -> None:
    global _step_count, _step_notify_every, _step_message, _step_subject, _step_config
    _step_count = 0
    _step_notify_every = None
    _step_message = "Training still running"
    _step_subject = None
    _step_config = None


def _maybe_write_run_log(config: Dict[str, Any]) -> Optional[str]:
    settings = config_module.get_logging_settings(config)
    if not settings.get("enabled"):
        return None

    path = settings.get("path") or config_module.DEFAULT_RUN_LOG_PATH
    path = config_module.resolve_path(config, path)

    payload = {
        "status": _state.status,
        "start_time": _isoformat(_state.start_time),
        "end_time": _isoformat(_state.end_time),
        "runtime_seconds": _state.runtime_seconds,
        "error_type": _state.error_type,
        "error_message": _state.error_message,
        "summary": _state.summary,
        "metrics": logger.get_metrics(),
    }

    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
    except OSError as exc:
        raise TrainWatchError(f"Failed to write run log to {path}") from exc

    return path


def _isoformat(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None
