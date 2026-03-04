"""Custom exceptions for TrainWatch."""


class TrainWatchError(Exception):
    """Base error for TrainWatch."""


class ConfigurationError(TrainWatchError):
    """Raised when configuration is invalid or missing."""


class NotificationError(TrainWatchError):
    """Raised when a notification fails to send."""


class MonitorError(TrainWatchError):
    """Raised when monitor state is invalid."""
