"""Custom exceptions for TrainWatcher."""


class TrainWatcherError(Exception):
    """Base error for TrainWatcher."""


class ConfigurationError(TrainWatcherError):
    """Raised when configuration is invalid or missing."""


class NotificationError(TrainWatcherError):
    """Raised when a notification fails to send."""


class MonitorError(TrainWatcherError):
    """Raised when monitor state is invalid."""
