"""Notification engine and channel routing."""

from dataclasses import dataclass
from typing import Iterable, List, Optional

from .notifications.email_notifier import EmailNotifier
from .notifications.telegram_notifier import TelegramNotifier


class Notifier:
    """Base notifier interface."""

    def send(self, message: str) -> None:
        raise NotImplementedError


@dataclass
class NotificationEngine:
    email: Optional[EmailNotifier] = None
    telegram: Optional[TelegramNotifier] = None

    def send(self, message: str, channels: Optional[Iterable[str]] = None) -> List[str]:
        """Send a message through the selected channels.

        Returns a list of channels that were attempted.
        """
        if not message:
            raise ValueError("message must be a non-empty string")

        selected = self._resolve_channels(channels)
        attempted: List[str] = []

        for channel in selected:
            if channel == "email" and self.email is not None:
                self.email.send(message)
                attempted.append("email")
            elif channel == "telegram" and self.telegram is not None:
                self.telegram.send(message)
                attempted.append("telegram")

        return attempted

    def _resolve_channels(self, channels: Optional[Iterable[str]]) -> List[str]:
        if channels is None:
            return self.available_channels()
        selected = [c.strip().lower() for c in channels]
        return [c for c in selected if c in {"email", "telegram"}]

    def available_channels(self) -> List[str]:
        channels: List[str] = []
        if self.email is not None:
            channels.append("email")
        if self.telegram is not None:
            channels.append("telegram")
        return channels
