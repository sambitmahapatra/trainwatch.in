"""Error formatting helpers."""

from typing import Optional, Tuple


def stringify_exception(exc: Optional[BaseException]) -> Tuple[str, Optional[str]]:
    """Return a safe (type, message) tuple for an exception."""
    if exc is None:
        return "Exception", None
    exc_type = exc.__class__.__name__
    message = str(exc)
    return exc_type, message or None
