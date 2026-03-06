"""Time formatting helpers."""

from typing import Optional


def format_duration(seconds: Optional[float]) -> str:
    """Format a duration in seconds into a human-friendly string."""
    if seconds is None:
        return "n/a"
    if seconds < 0:
        seconds = 0.0

    total_seconds = int(round(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    return f"{secs}s"
