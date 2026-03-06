"""Public convenience APIs for TrainWatcher."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from . import config as config_module
from . import monitor


def watch(
    train_fn: Callable[..., Any],
    *args: Any,
    interpretation: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Any:
    """Run a training callable with automatic TrainWatcher lifecycle handling."""
    run_config = dict(config or {})
    if interpretation:
        run_config = config_module.deep_merge(
            run_config,
            {"interpretation": {"mode": interpretation}},
        )

    monitor.start()
    try:
        result = train_fn(*args, **kwargs)
    except Exception as exc:
        monitor.fail(exc, config=run_config)
        raise
    else:
        monitor.end(config=run_config)
        return result
